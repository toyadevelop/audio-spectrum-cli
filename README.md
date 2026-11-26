# audio-spectrum-cli

WAVファイルを読み込み、時間波形と窓関数を適用したFFT周波数スペクトルを1枚のPNGに描画するPython CLIです。モノラル・マルチチャンネルのPCM/float WAVに対応し、マルチチャンネル音声は解析前にモノラルへミックスします。

## セットアップ

Python 3.11以降を用意し、依存ライブラリをインストールします。

```bash
python -m pip install -r requirements.txt
```

## テスト音源の生成

440 Hzと1000 Hzのサイン波に微弱なホワイトノイズを加えた、48 kHz・16-bit・2秒のWAVを生成します。乱数シードを固定しているため、生成結果を再現できます。

```bash
python generate_test_wav.py
```

出力先を変える場合:

```bash
python generate_test_wav.py --output sample.wav
```

## 解析

```bash
python analyze.py sample.wav --output result.png --n-fft 2048
```

- 上段: 時間 [s] と振幅 [-1, 1]
- 下段: 20 Hz〜20 kHzの対数周波数軸と振幅 [dBFS]
- FFT前にHann窓を適用し、50%オーバーラップのフレームの振幅スペクトルを平均します。
- `--n-fft` は窓長とFFTサイズです。大きくすると周波数分解能が上がり、時間方向の平均回数は少なくなります。
- 入力ファイルが見つからない場合や、不正なWAVの場合はエラー内容を表示して終了します。

## 出力例

下図は同梱の `sample.wav` を `--n-fft 2048` で解析した画像です。

![440 Hzと1000 Hzのピークを含む時間波形と周波数スペクトル](docs/result.png)

