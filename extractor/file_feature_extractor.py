import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import AgglomerativeClustering

from pathlib import Path

class Song:
    """
    A class to hold and extract key audio features from a song file
    for AI DJ applications.
    """
    def __init__(self, file_path: str):
        """
        Initializes the Song object by loading the audio and extracting features.

        Args:
            file_path (str): The path to the audio file.
        """
        print(f"Analyzing '{file_path}'...")
        self.file_path = file_path
        
        # Load audio with a standard sample rate for consistency
        self.y, self.sr = librosa.load(file_path, sr=22050)
        
        # --- Extract all features ---
        self._extract_features()
        print("Analysis complete.")

    def _extract_features(self):
        """
        Private method to run all feature extraction processes.
        """
        # --- 1. Global Features (song-wide) ---
        self.duration = librosa.get_duration(y=self.y, sr=self.sr)
        self.rms_energy = np.mean(librosa.feature.rms(y=self.y))

        # --- 2. Temporal Features (time-based) ---
        # Call beat_track once for efficiency
        tempo, beat_frames = librosa.beat.beat_track(y=self.y, sr=self.sr)
        print(f"Tempo: {tempo}")
        print(f"Beat frames: {beat_frames}")
        # FIX: Ensure tempo is a scalar by taking the mean, in case beat_track returns an array
        self.tempo = np.mean(tempo)
        self.beats = librosa.frames_to_time(beat_frames, sr=self.sr)
        self.onsets = librosa.onset.onset_detect(y=self.y, sr=self.sr, units='time')

        # --- 3. Spectral & Component Features ---
        # Separate into harmonic (vocals, melody) and percussive (drums)
        self.y_harmonic, self.y_percussive = librosa.effects.hpss(self.y)

        # Mel-spectrogram for frequency analysis
        self.melspec = librosa.feature.melspectrogram(y=self.y, sr=self.sr)
        
        # Get energy for bass, mids, and treble bands over time
        self.bass_energy = self._get_spectral_band_energy(self.melspec, (20, 250))
        self.mid_energy = self._get_spectral_band_energy(self.melspec, (250, 4000))
        self.treble_energy = self._get_spectral_band_energy(self.melspec, (4000, 20000))
        
        # --- 4. Structural Features ---
        # Use MFCCs and a recurrence matrix to find structurally similar segments
        # This is a common way to approximate sections like verse/chorus
        mfccs = librosa.feature.mfcc(y=self.y, sr=self.sr)
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr)
        stacked_features = np.vstack([mfccs, chroma])
        
        R = librosa.segment.recurrence_matrix(stacked_features, width=5, mode='affinity', sym=True)
        
        # Use clustering to find segment boundaries
        n_segments = 8 # You can tune this number
        clusterer = AgglomerativeClustering(n_clusters=n_segments, linkage='ward')
        # Use (1 - R) because clustering works on distances, and affinity is a similarity measure
        segment_labels = clusterer.fit_predict(1 - R)
        # Find the points where the label changes
        boundaries = np.where(np.diff(segment_labels))[0]
        self.segment_boundaries = librosa.frames_to_time(boundaries, sr=self.sr)
        self.segment_labels = segment_labels

        # --- 5. Vector Representation ---
        # Create a simple, aggregated feature vector for quick comparisons
        self.feature_vector = np.array([
            self.tempo,
            self.rms_energy,
            np.mean(self.bass_energy),
            np.mean(self.mid_energy),
            np.mean(self.treble_energy),
            np.std(self.bass_energy), # Add standard deviation for dynamics
            np.std(self.mid_energy),
            np.std(self.treble_energy)
        ])

    def _get_spectral_band_energy(self, melspec, freq_range_hz):
        """Helper to calculate energy in a specific frequency band."""
        freqs = librosa.mel_frequencies(n_mels=melspec.shape[0], fmin=0, fmax=self.sr/2)
        
        # Find the mel bands corresponding to the frequency range
        start_band = np.argmin(np.abs(freqs - freq_range_hz[0]))
        end_band = np.argmin(np.abs(freqs - freq_range_hz[1]))
        
        # Sum the energy in those bands for each time frame
        band_energy = np.sum(melspec[start_band:end_band+1, :], axis=0)
        return band_energy
        
    def summarize(self):
        """Prints a summary of the extracted features."""
        print("\n--- Song Analysis Summary ---")
        print(f"File: {self.file_path}")
        print(f"Duration: {self.duration:.2f} seconds")
        print(f"Tempo (BPM): {self.tempo:.2f}")
        print(f"Average Energy (RMS): {self.rms_energy:.4f}")
        print(f"Detected Beats: {len(self.beats)} at times {self.beats[:5].round(2)}... ")
        print(f"Detected Onsets: {len(self.onsets)}")
        print(f"Found {len(self.segment_boundaries) + 1} structural segments.")
        print(f"  - Boundaries at (s): {self.segment_boundaries.round(2)}")
        print(f"Aggregated Feature Vector: {self.feature_vector.round(2)}")
        print("---------------------------\n")

    def plot_features(self, show: bool = True, plot_path: Path = None):
        """
        Creates and displays a comprehensive plot of the song's main features.
        """
        fig, ax = plt.subplots(nrows=4, ncols=1, sharex=True, figsize=(15, 20))
        fig.suptitle('Song Feature Analysis', fontsize=16)

        # --- Plot 1: Waveform with Beats and Onsets ---
        librosa.display.waveshow(self.y, sr=self.sr, ax=ax[0], alpha=0.6, label='Waveform')
        ax[0].vlines(self.beats, -1, 1, color='r', linestyle='--', label='Beats')
        ax[0].vlines(self.onsets, -1, 1, color='g', linestyle=':', label='Onsets')
        ax[0].set_title('Waveform, Beats, and Onsets')
        ax[0].set_ylabel('Amplitude')
        ax[0].legend()
        ax[0].grid(True)

        # --- Plot 2: Spectral Band Energy ---
        times = librosa.times_like(self.bass_energy, sr=self.sr)
        ax[1].plot(times, self.bass_energy, label='Bass Energy', color='b')
        ax[1].plot(times, self.mid_energy, label='Mid Energy', color='g')
        ax[1].plot(times, self.treble_energy, label='Treble Energy', color='r')
        ax[1].set_title('Spectral Band Energy')
        ax[1].set_ylabel('Magnitude')
        ax[1].legend()
        ax[1].grid(True)
        
        # --- Plot 3: Harmonic vs. Percussive Components ---
        librosa.display.waveshow(self.y_harmonic, sr=self.sr, ax=ax[2], alpha=0.6, label='Harmonic')
        librosa.display.waveshow(self.y_percussive, sr=self.sr, ax=ax[2], alpha=0.6, color='r', label='Percussive')
        ax[2].set_title('Harmonic vs. Percussive Components')
        ax[2].set_ylabel('Amplitude')
        ax[2].legend()
        ax[2].grid(True)

        # --- Plot 4: Mel Spectrogram with Structural Segments ---
        melspec_db = librosa.power_to_db(self.melspec, ref=np.max)
        librosa.display.specshow(melspec_db, sr=self.sr, x_axis='time', y_axis='mel', ax=ax[3])
        ax[3].vlines(self.segment_boundaries, 0, self.sr/2, color='w', linestyle='--', label='Segments')
        ax[3].set_title('Mel Spectrogram and Structural Segments')
        ax[3].set_ylabel('Frequency (Mel)')
        ax[3].legend()

        plt.xlabel('Time (s)')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust layout to make room for suptitle
        
        if plot_path: plt.savefig(plot_path / f"{Path(self.file_path).stem}.png")
        if show: plt.show()
        
        plt.close()


# --- Example Usage ---
if __name__ == '__main__':
    # Define paths to your audio files
    mix_path = "/home/brett/Desktop/pers/soundbits/soundcloud/downloads/mixes/Christopher Tubbs - Christopher Tubbs' Caravan 'Enfants De La Nuit' Mix.mp3"
    song_path = "/home/brett/Desktop/pers/soundbits/soundcloud/downloads/songs/Sneakyyy - Infinite.mp3"
    
    plot_path = Path("/home/brett/Desktop/pers/soundbits/extractor/plots")
    try:
        # Create a song object, which automatically processes the file
        song_object = Song(song_path)
        
        # Print the summary of the extracted features
        song_object.summarize()
        
        # Visualize the features
        song_object.plot_features(plot_path=plot_path)
        
    except Exception as e:
        print(f"An error occurred: {e}")
