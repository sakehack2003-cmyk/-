# Floor Template App (MVP)

iPhone 15 Pro (LiDAR) でスキャンした点群/メッシュから、床の型紙を生成して Illustrator で編集できる PDF/SVG を出力するためのデスクトップアプリです。MVP では **点群(.ply)のE2E** を最優先にし、**自動8割 + 2Dで最終手修正** を想定しています。

## 主要機能 (MVP)
- PLY読み込み (点群). OBJ/STL/GLB は **未対応** (UIで明示)。
- 点群の統計表示 (点数/BBox)。
- RANSAC で床候補平面を最大3件抽出。
- 床点抽出 (距離閾値 + Zバンド)。
- 2D 投影 → 外周輪郭生成 (簡易 alpha-shape)。
- 外周/穴の2D編集 (頂点ドラッグ、穴の追加)。
- PDF/SVG ベクター出力 (100mm スケールバー/注記あり)。
- JSON プロジェクト保存/再読込。

## 実行手順

```bash
cd floor-template-app
python -m venv .venv
source .venv/bin/activate  # Windowsは .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## 使い方の流れ
1. **Import** で .ply を読み込む。
2. **Detect Floor** で床候補を検出し、ラジオボタンで選択。
3. **Generate Outline** で床点抽出 → 2D投影 → 輪郭生成。
4. **Scale Calibrate** で2点をクリックし、実測距離(mm)を入力。
5. 2Dビューで頂点編集/穴追加。
6. **Export PDF/SVG** で出力。

## PyInstaller (雛形)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile app/main.py --name FloorTemplateApp
```

## MVPの制約
- Open3D の 3D ビューは **別ウィンドウ** で表示。
- OBJ/STL/GLB の読み込みは UI で未対応として案内。
- 2D編集は最小限 (頂点ドラッグ、簡易 Undo/Redo)。
- 輪郭生成は簡易 alpha-shape 近似。

## 今後の拡張点
- 3Dビューの Qt 組み込み (Open3D + QtWidget)。
- OBJ/STL/GLB の安定読み込み。
- より高精度な concave hull。
- 2D編集のスナップ/グリッド強化。
- 印刷タイル分割出力。
