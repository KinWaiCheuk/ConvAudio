import pytest
import librosa
import torch
import matplotlib.pyplot as plt
from scipy.signal import chirp, sweep_poly
from nnAudio.Spectrogram import *

gpu_idx=1

# librosa example audio for testing
example_y, example_sr = librosa.load(librosa.util.example_audio_file())


def test_stft_complex():
    x = example_y
    stft = STFT(n_fft=2048, hop_length=512, device='cpu')
    X = stft(torch.tensor(x).unsqueeze(0), output_format="Complex")
    X_real, X_imag = X[:, :, :, 0].squeeze().numpy(), X[:, :, :, 1].squeeze().numpy()
    X_librosa = librosa.stft(x, n_fft=2048, hop_length=512)
    real_diff, imag_diff = np.allclose(X_real, X_librosa.real, rtol=1e-3, atol=1e-3), \
                            np.allclose(X_imag, X_librosa.imag, rtol=1e-3, atol=1e-3)
    
    assert real_diff and imag_diff
    
def test_stft_complex_winlength():
    x = example_y
    stft = STFT(n_fft=512, win_length=400, hop_length=128, device='cpu')
    X = stft(torch.tensor(x).unsqueeze(0), output_format="Complex")
    X_real, X_imag = X[:, :, :, 0].squeeze().numpy(), X[:, :, :, 1].squeeze().numpy()
    X_librosa = librosa.stft(x, n_fft=512, win_length=400, hop_length=128)
    real_diff, imag_diff = np.allclose(X_real, X_librosa.real, rtol=1e-3, atol=1e-3), \
                            np.allclose(X_imag, X_librosa.imag, rtol=1e-3, atol=1e-3)
    assert real_diff and imag_diff    
    
    
def test_stft_complex_GPU():
    x = example_y
    stft = STFT(n_fft=2048, hop_length=512, device=f'cuda:{gpu_idx}')
    X = stft(torch.tensor(x,device=f'cuda:{gpu_idx}').unsqueeze(0), output_format="Complex")
    X_real, X_imag = X[:, :, :, 0].squeeze().detach().cpu(), X[:, :, :, 1].squeeze().detach().cpu()
    X_librosa = librosa.stft(x, n_fft=2048, hop_length=512)
    real_diff, imag_diff = np.allclose(X_real, X_librosa.real, rtol=1e-3, atol=1e-3), \
                            np.allclose(X_imag, X_librosa.imag, rtol=1e-3, atol=1e-3)
    
    assert real_diff and imag_diff    
            

def test_stft_magnitude():
    x = example_y
    stft = STFT(n_fft=2048, hop_length=512, device='cpu')
    X = stft(torch.tensor(x).unsqueeze(0), output_format="Magnitude").squeeze().numpy()
    X_librosa, _ = librosa.core.magphase(librosa.stft(x, n_fft=2048, hop_length=512))
    assert np.allclose(X, X_librosa, rtol=1e-3, atol=1e-3)


def test_stft_phase():
    x = example_y
    stft = STFT(n_fft=2048, hop_length=512, device='cpu')
    X = stft(torch.tensor(x).unsqueeze(0), output_format="Phase")
    X_real, X_imag = torch.cos(X).squeeze().numpy(), torch.sin(X).squeeze().numpy()
    _, X_librosa = librosa.core.magphase(librosa.stft(x, n_fft=2048, hop_length=512))

    real_diff, imag_diff = np.mean(np.abs(X_real - X_librosa.real)), \
                            np.mean(np.abs(X_imag - X_librosa.imag))

    # I find that np.allclose is too strict for allowing phase to be similar to librosa.
    # Hence for phase we use average element-wise distance as the test metric.
    assert real_diff < 2e-4 and imag_diff < 2e-4


def test_mel_spectrogram():
    x = example_y
    melspec = MelSpectrogram(n_fft=2048, hop_length=512, device='cpu')
    X = melspec(torch.tensor(x).unsqueeze(0)).squeeze().numpy()
    X_librosa = librosa.feature.melspectrogram(x, n_fft=2048, hop_length=512)
    assert np.allclose(X, X_librosa, rtol=1e-3, atol=1e-3)


def test_cqt_1992_v2_log():
    # Log sweep case
    fs = 44100
    t = 1
    f0 = 55
    f1 = 22050
    s = np.linspace(0, t, fs*t)
    x = chirp(s, f0, 1, f1, method='logarithmic')
    x = x.astype(dtype=np.float32)

    # Magnitude
    stft = CQT1992v2(sr=fs, fmin=55, device='cpu', output_format="Magnitude",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/log-sweep-cqt-1992-mag-ground-truth.npy")
    X = np.log(X + 1e-5)
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Complex
    stft = CQT1992v2(sr=fs, fmin=55, device='cpu', output_format="Complex",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/log-sweep-cqt-1992-complex-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Phase
    stft = CQT1992v2(sr=fs, fmin=55, device='cpu', output_format="Phase",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/log-sweep-cqt-1992-phase-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)


def test_cqt_1992_v2_linear():
    # Linear sweep case
    fs = 44100
    t = 1
    f0 = 55
    f1 = 22050
    s = np.linspace(0, t, fs*t)
    x = chirp(s, f0, 1, f1, method='linear')
    x = x.astype(dtype=np.float32)

    # Magnitude
    stft = CQT1992v2(sr=fs, fmin=55, device='cpu', output_format="Magnitude",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/linear-sweep-cqt-1992-mag-ground-truth.npy")
    X = np.log(X + 1e-5)
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Complex
    stft = CQT1992v2(sr=fs, fmin=55, device='cpu', output_format="Complex",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/linear-sweep-cqt-1992-complex-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Phase
    stft = CQT1992v2(sr=fs, fmin=55, device='cpu', output_format="Phase",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/linear-sweep-cqt-1992-phase-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)


def test_cqt_2010_v2_log():
    # Log sweep case
    fs = 44100
    t = 1
    f0 = 55
    f1 = 22050
    s = np.linspace(0, t, fs*t)
    x = chirp(s, f0, 1, f1, method='logarithmic')
    x = x.astype(dtype=np.float32)

    # Magnitude
    stft = CQT2010v2(sr=fs, fmin=55, device='cpu', output_format="Magnitude",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0))
    ground_truth = np.load("tests/ground-truths/log-sweep-cqt-2010-mag-ground-truth.npy")
    X = np.log(X.numpy() + 1e-5)
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Complex
    stft = CQT2010v2(sr=fs, fmin=55, device='cpu', output_format="Complex",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/log-sweep-cqt-2010-complex-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Phase
    stft = CQT2010v2(sr=fs, fmin=55, device='cpu', output_format="Phase",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/log-sweep-cqt-2010-phase-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)


def test_cqt_2010_v2_linear():
    # Linear sweep case
    fs = 44100
    t = 1
    f0 = 55
    f1 = 22050
    s = np.linspace(0, t, fs*t)
    x = chirp(s, f0, 1, f1, method='linear')
    x = x.astype(dtype=np.float32)

    # Magnitude
    stft = CQT2010v2(sr=fs, fmin=55, device='cpu', output_format="Magnitude",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0))
    ground_truth = np.load("tests/ground-truths/linear-sweep-cqt-2010-mag-ground-truth.npy")
    X = np.log(X.numpy() + 1e-5)
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Complex
    stft = CQT2010v2(sr=fs, fmin=55, device='cpu', output_format="Complex",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/linear-sweep-cqt-2010-complex-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)

    # Phase
    stft = CQT2010v2(sr=fs, fmin=55, device='cpu', output_format="Phase",
                     n_bins=207, bins_per_octave=24)
    X = stft(torch.tensor(x).unsqueeze(0)).numpy()
    ground_truth = np.load("tests/ground-truths/linear-sweep-cqt-2010-phase-ground-truth.npy")
    assert np.allclose(X, ground_truth, rtol=1e-3, atol=1e-3)


def test_mfcc():
    x = example_y
    mfcc = MFCC(device='cpu', sr=example_sr)
    X = mfcc(torch.tensor(x).unsqueeze(0)).squeeze().numpy()
    X_librosa = librosa.feature.mfcc(x, sr=example_sr)
    assert np.allclose(X, X_librosa, rtol=1e-3, atol=1e-3)


def test_inverse():
    x = example_y
    stft = STFT(n_fft=2048, hop_length=512, device='cpu')
    X = stft(torch.tensor(x).unsqueeze(0), output_format="Complex")
    x_recon = stft.inverse(X).numpy().squeeze()
    
    # I find that np.allclose is too strict for inverse reconstruction.
    # Hence for inverse we use average element-wise distance as the test metric.
    diff = np.mean(np.abs(x_recon - x))
    assert diff < 1e-3
