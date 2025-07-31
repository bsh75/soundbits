import torch
import torchaudio
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import AgglomerativeClustering
from scipy.spatial.distance import pdist, squareform
import librosa # Kept for specific high-level functions not in torchaudio
from pathlib import Path

class SongTorchaudio:
    """
    A class to hold and extract key audio features from a song file
    for AI DJ applications, using torchaudio as the primary backend.
    """
    def __init__(self, file_path: str, n_fft=2048, hop_length=512, n_mels=128):
        """
        Initializes the Song object by loading the audio and extracting features.

        Args:
            file_path (str): The path to the audio file.
            n_fft (int): The number of samples in an FFT window.
            hop_length (int): The number of samples between successive frames.
            n_mels (int): The number of mel bands to generate.
        """
        print(f"Analyzing '{file_path}' with torchaudio...")
        self.file_path = file_path
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels

        # --- Load Audio with Torchaudio ---
        # This returns a tensor and the sample rate
        waveform, self.sr = torchaudio.load(file_path)

        # --- Ensure Mono for consistency ---
        # If stereo, average the channels. Most audio analysis is done in mono.
        if waveform.shape[0] > 1:
            self.waveform = torch.mean(waveform, dim=0, keepdim=True)
        else:
            self.waveform = waveform

        # For librosa functions, we'll need a numpy representation
        self.y_np = self.waveform.squeeze().numpy()

        # --- Extract all features ---
        self._extract_features()
        print("Analysis complete.")

    def _extract_features(self):
        """
        Private method to run all feature extraction processes.
        """
        # --- 1. Global Features (song-wide) ---
        self.duration = self.waveform.shape[1] / self.sr
        
        # Use torchaudio's RMS transform
        rms_transform = torchaudio.transforms.RMS(frame_length=self.n_fft, hop_length=self.hop_length)
        self.rms_energy = rms_transform(self.waveform).mean().item()

        # --- 2. Temporal Features (using librosa for high-level analysis) ---
        # Torchaudio does not have a direct, high-level beat tracker.
        # Librosa's implementation is sophisticated and well-suited for this.
        tempo, beat_frames = librosa.beat.beat_track(y=self.y_np, sr=self.sr, hop_length=self.hop_length)
        self.tempo = np.mean(tempo)
        self.beats = librosa.frames_to_time(beat_frames, sr=self.sr, hop_length=self.hop_length)
        self.onsets = librosa.onset.onset_detect(y=self.y_np, sr=self.sr, hop_length=self.hop_length, units='time')

        # --- 3. Spectral & Component Features ---
        # HPSS (Harmonic-Percussive Source Separation) is another complex algorithm
        # where we'll rely on librosa's implementation.
        self.y_harmonic, self.y_percussive = librosa.effects.hpss(self.y_np)

        # Mel-spectrogram using torchaudio transforms
        melspec_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=self.sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels
        )
        self.melspec = melspec_transform(self.waveform).squeeze(0) # Squeeze batch dim

        # Get energy for bass, mids, and treble bands over time
        self.bass_energy = self._get_spectral_band_energy(self.melspec, (20, 250))
        self.mid_energy = self._get_spectral_band_energy(self.melspec, (250, 4000))
        self.treble_energy = self._get_spectral_band_energy(self.melspec, (4000, 20000))

        # --- 4. Structural Features ---
        # MFCCs using torchaudio
        mfcc_transform = torchaudio.transforms.MFCC(
            sample_rate=self.sr,
            n_mfcc=13,
            melkwargs={'n_fft': self.n_fft, 'hop_length': self.hop_length, 'n_mels': self.n_mels}
        )
        mfccs = mfcc_transform(self.waveform).squeeze(0).numpy()

        # Chroma features are often better with CQT, so we use librosa here.
        chroma = librosa.feature.chroma_cqt(y=self.y_np, sr=self.sr, hop_length=self.hop_length)
        
        # Combine features for segmentation
        # Ensure they have the same number of frames
        min_frames = min(mfccs.shape[1], chroma.shape[1])
        stacked_features = np.vstack([mfccs[:, :min_frames], chroma[:, :min_frames]])

        # Build a recurrence matrix using scipy (replaces librosa.segment.recurrence_matrix)
        # We compute pairwise distances and convert to an affinity matrix.
        R_dist = pdist(stacked_features.T, metric='euclidean')
        R_sq = squareform(R_dist)
        R_affinity = 1 - (R_sq / np.max(R_sq))
        
        # Use clustering to find segment boundaries
        n_segments = 8 # You can tune this number
        clusterer = AgglomerativeClustering(n_clusters=n_segments, linkage='ward')
        segment_labels = clusterer.fit_predict(1 - R_affinity)
        
        # Find the points where the label changes
        boundaries = np.where(np.diff(segment_labels))[0]
        self.segment_boundaries = librosa.frames_to_time(boundaries, sr=self.sr, hop_length=self.hop_length)
        self.segment_labels = segment_labels

        # --- 5. Vector Representation ---
        # Create a simple, aggregated feature vector for quick comparisons
        self.feature_vector = np.array([
            self.tempo,
            self.rms_energy,
            np.mean(self.bass_energy),
            np.mean(self.mid_energy),
            np.mean(self.treble_energy),
            np.std(self.bass_energy),
            np.std(self.mid_energy),
            np.std(self.treble_energy)
        ])

    def _get_spectral_band_energy(self, melspec_tensor, freq_range_hz):
        """Helper to calculate energy in a specific frequency band from a torchaudio melspec."""
        # Use librosa's utility to get mel frequency centers
        mel_freqs = librosa.mel_frequencies(n_mels=self.n_mels, fmin=0, fmax=self.sr/2)
        
        # Find the mel bands corresponding to the frequency range
        start_band = np.argmin(np.abs(mel_freqs - freq_range_hz[0]))
        end_band = np.argmin(np.abs(mel_freqs - freq_range_hz[1]))
        
        # Sum the energy in those bands for each time frame
        # Convert tensor to numpy for this operation
        band_energy = np.sum(melspec_tensor.numpy()[start_band:end_band+1, :], axis=0)
        return band_energy

    def summarize(self):
        """Prints a summary of the extracted features."""
        print("\n--- Song Analysis Summary (Torchaudio) ---")
        print(f"File: {self.file_path}")
        print(f"Duration: {self.duration:.2f} seconds")
        print(f"Tempo (BPM): {self.tempo:.2f}")
        print(f"Average Energy (RMS): {self.rms_energy:.4f}")
        print(f"Detected Beats: {len(self.beats)} at times {self.beats[:5].round(2)}... ")
        print(f"Detected Onsets: {len(self.onsets)}")
        print(f"Found {len(self.segment_boundaries) + 1} structural segments.")
        print(f"  - Boundaries at (s): {self.segment_boundaries.round(2)}")
        print(f"Aggregated Feature Vector: {self.feature_vector.round(2)}")
        print("------------------------------------------\n")

    def plot_features(self, show: bool = True, plot_path: Path = None):
        """
        Creates and displays a comprehensive plot using Matplotlib.
        """
        fig, ax = plt.subplots(nrows=4, ncols=1, sharex=True, figsize=(15, 20))
        fig.suptitle('Song Feature Analysis (Torchaudio Backend)', fontsize=16)

        # --- Plot 1: Waveform with Beats and Onsets ---
        time_axis = np.linspace(0, self.duration, num=self.waveform.shape[1])
        ax[0].plot(time_axis, self.y_np, alpha=0.6, label='Waveform')
        ax[0].vlines(self.beats, -1, 1, color='r', linestyle='--', label='Beats')
        ax[0].vlines(self.onsets, -1, 1, color='g', linestyle=':', label='Onsets')
        ax[0].set_title('Waveform, Beats, and Onsets')
        ax[0].set_ylabel('Amplitude')
        ax[0].set_ylim(-1, 1)
        ax[0].legend()
        ax[0].grid(True)

        # --- Plot 2: Spectral Band Energy ---
        times = librosa.times_like(self.bass_energy, sr=self.sr, hop_length=self.hop_length)
        ax[1].plot(times, self.bass_energy, label='Bass Energy', color='b')
        ax[1].plot(times, self.mid_energy, label='Mid Energy', color='g')
        ax[1].plot(times, self.treble_energy, label='Treble Energy', color='r')
        ax[1].set_title('Spectral Band Energy')
        ax[1].set_ylabel('Magnitude')
        ax[1].legend()
        ax[1].grid(True)

        # --- Plot 3: Harmonic vs. Percussive Components ---
        ax[2].plot(time_axis, self.y_harmonic, alpha=0.6, label='Harmonic')
        ax[2].plot(time_axis, self.y_percussive, alpha=0.6, color='r', label='Percussive')
        ax[2].set_title('Harmonic vs. Percussive Components')
        ax[2].set_ylabel('Amplitude')
        ax[2].legend()
        ax[2].grid(True)

        # --- Plot 4: Mel Spectrogram with Structural Segments ---
        # Convert power spectrogram to decibels for visualization
        db_transform = torchaudio.transforms.AmplitudeToDB(stype='power', top_db=80)
        melspec_db = db_transform(self.melspec)
        
        # Use matplotlib's pcolormesh for the spectrogram
        img = ax[3].pcolormesh(times, librosa.mel_frequencies(n_mels=self.n_mels), melspec_db.numpy(), 
                               shading='gouraud', cmap='magma')
        fig.colorbar(img, ax=ax[3], format='%+2.0f dB')
        
        ax[3].vlines(self.segment_boundaries, 0, self.sr/2, color='w', linestyle='--', label='Segments')
        ax[3].set_title('Mel Spectrogram and Structural Segments')
        ax[3].set_ylabel('Frequency (Hz)')
        ax[3].legend(loc='upper right')

        plt.xlabel('Time (s)')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        if plot_path: plt.savefig(plot_path / f"{Path(self.file_path).stem}_ta.png")
            
        if show: plt.show()
            
        plt.close()


# --- Example Usage ---
if __name__ == '__main__':
    # IMPORTANT: Replace these paths with the actual paths to your audio files and output directory.
    # The script will not run if these paths are incorrect.
    try:
        # Define paths to your audio files
        # Using a placeholder - you MUST change this.
        song_path = "/home/brett/Desktop/pers/soundbits/soundcloud/downloads/songs/Sneakyyy - Infinite.mp3" 
        
        # Define path for saving plots
        # Using a placeholder - you MUST change this.
        plot_path = Path("/home/brett/Desktop/pers/soundbits/extractor/plots")

        # Create a song object, which automatically processes the file
        song_object = SongTorchaudio(song_path)
        
        # Print the summary of the extracted features
        song_object.summarize()
        
        # Visualize the features
        song_object.plot_features(show=True, plot_path=plot_path)
        
    except FileNotFoundError:
        print("\n--- ERROR ---")
        print(f"Could not find the audio file at the specified path: '{song_path}'")
        print("Please update the 'song_path' and 'plot_path' variables in the '__main__' block of the script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please ensure you have installed all required libraries: torch, torchaudio, numpy, matplotlib, scikit-learn, scipy, ncll and librosa.")

