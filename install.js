module.exports = {
  requires: {
    bundle: "ai"
  },
  run: [
    {
      when: "{{!exists('app/stable-audio-3')}}",
      method: "shell.run",
      params: {
        message: "git clone https://github.com/Stability-AI/stable-audio-3.git app/stable-audio-3"
      }
    },
    {
      when: "{{!exists('app/stabledaw')}}",
      method: "shell.run",
      params: {
        message: "git clone https://github.com/gantasmo/stabledaw.git app/stabledaw"
      }
    },
    {
      when: "{{!exists('app/tascar')}}",
      method: "shell.run",
      params: {
        message: "git clone https://github.com/gisogrimm/tascar.git app/tascar"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/dashboard",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app/stable-audio-3",
        message: [
          "uv sync --extra ui --active"
        ]
      }
    },
    {
      when: "{{gpu === 'nvidia' && (platform === 'win32' || platform === 'linux')}}",
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app/stable-audio-3",
          flashattention: true
        }
      }
    },
    {
      when: "{{platform === 'darwin' && !exists('app/tascar/build')}}",
      method: "shell.run",
      params: {
        path: "app/tascar",
        message: [
          "brew install jack libsndfile liblo libltc gtkmm3 libxml++ fftw boost gsl eigen libsamplerate portaudio liblsl cmake pkg-config doxygen 2>/dev/null || true",
          "make -j$(sysctl -n hw.ncpu)"
        ]
      }
    },
    {
      when: "{{platform === 'linux' && !exists('app/tascar/build')}}",
      method: "shell.run",
      params: {
        path: "app/tascar",
        message: [
          "sudo apt-get update && sudo apt-get install -y build-essential default-jre doxygen dpkg-dev g++ git imagemagick jackd2 libasound2-dev libboost-all-dev libcairomm-1.0-dev libeigen3-dev libfftw3-dev libfftw3-double3 libfftw3-single3 libgsl-dev libgtkmm-3.0-dev libgtksourceviewmm-3.0-dev libjack-jackd2-dev liblo-dev libltc-dev libmatio-dev libsndfile1-dev libwebkit2gtk-4.0-dev libxml++2.6-dev lsb-release make portaudio19-dev ruby-dev software-properties-common texlive-latex-extra texlive-latex-recommended vim-common wget libsamplerate0-dev cmake 2>/dev/null || true",
          "make -j$(nproc)"
        ]
      }
    },
    {
      when: "{{!exists('app/stabledaw-pinokio-git/frontend/node_modules')}}",
      method: "shell.run",
      params: {
        path: "app/stabledaw-pinokio-git/frontend",
        message: [
          "npm ci"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/stabledaw-pinokio-git/frontend",
        message: [
          "npm run build"
        ]
      }
    },
    {
      when: "{{!exists('app/volt-dashboard/node_modules')}}",
      method: "shell.run",
      params: {
        path: "app/volt-dashboard",
        message: [
          "npm ci"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app/volt-dashboard",
        message: [
          "npm run build"
        ]
      }
    },
    {
      method: "notify",
      params: {
        html: "Install complete. Click Start to launch Omni Studio."
      }
    }
  ]
}