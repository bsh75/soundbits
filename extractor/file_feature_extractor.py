import librosa
import numpy as np
from sklearn.cluster import AgglomerativeClustering

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
        self.tempo, _ = librosa.beat.beat_track(y=self.y, sr=self.sr)
        self.rms_energy = np.mean(librosa.feature.rms(y=self.y))

        # --- 2. Temporal Features (time-based) ---
        self.beats = librosa.beat.beat_track(y=self.y, sr=self.sr, units='time')[1]
        self.onsets = librosa.onset.onset_detect(y=self.y, sr=self.sr, units='time')

        # --- 3. Spectral & Component Features ---
        # Separate into harmonic (vocals, melody) and percussive (drums)
        self.y_harmonic, self.y_percussive = librosa.effects.hpss(self.y)

        # Mel-spectrogram for frequency analysis
        melspec = librosa.feature.melspectrogram(y=self.y, sr=self.sr)
        
        # Get energy for bass, mids, and treble bands over time
        self.bass_energy = self._get_spectral_band_energy(melspec, (20, 250))
        self.mid_energy = self._get_spectral_band_energy(melspec, (250, 4000))
        self.treble_energy = self._get_spectral_band_energy(melspec, (4000, 20000))
        
        # --- 4. Structural Features ---
        # Use MFCCs and a recurrence matrix to find structurally similar segments
        # This is a common way to approximate sections like verse/chorus
        mfccs = librosa.feature.mfcc(y=self.y, sr=self.sr)
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr)
        # Stack features for segmentation
        stacked_features = np.vstack([mfccs, chroma])
        
        R = librosa.segment.recurrence_matrix(stacked_features, width=5, mode='affinity', sym=True)
        
        # Use clustering to find segment boundaries
        n_segments = 8 # You can tune this number
        clusterer = AgglomerativeClustering(n_clusters=n_segments, affinity='precomputed', linkage='ward')
        segment_labels = clusterer.fit_predict(1 - R)
        self.segment_boundaries = librosa.frames_to_time(
            np.where(np.diff(segment_labels))[0], sr=self.sr
        )
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


# --- Example Usage ---
if __name__ == '__main__':
    # You can replace this with your own audio file path
    # e.g., audio_file = 'path/to/your/song.mp3'
    # Using a built-in librosa example for demonstration
    audio_file = librosa.ex('C:\Users\bshoc\OneDrive\Code\soundbits\samples\luxury-fashion-348904.mp3')
    
    try:
        # Create a song object, which automatically processes the file
        song_object = Song(audio_file)
        
        # Print the summary of the extracted features
        song_object.summarize()
        
        # You can now access any feature directly
        # print("First 5 beat times:", song_object.beats[:5])
        # print("Tempo:", song_object.tempo)

    except Exception as e:
        print(f"An error occurred: {e}")