# Windows + Chrome での見方（最短）

## 1) フォルダを開く
このプロジェクトのフォルダをエクスプローラーで開く。

## 2) アドレスバーに `cmd` と入力して Enter
そのフォルダ位置でコマンドプロンプトが開く。

## 3) 次を実行
```bat
python -m http.server 8000
```

## 4) Chrome で次を開く
`http://localhost:8000/previews/index.html`

> `previews/index.html` を直接URL欄に入れても開けない場合があるため、
> 上の `localhost` 形式が確実です。

## 5) 停止方法
コマンドプロンプトに戻って `Ctrl + C`。

---

## うまくいかない時
- `python` がないと言われる: Pythonをインストール（インストール時に「Add Python to PATH」をON）。
- 8000番が使われている: `python -m http.server 8080` に変更し、
  `http://localhost:8080/previews/index.html` を開く。

## localhostが拒否されるとき（ERR_CONNECTION_REFUSED）
サーバー起動に失敗している状態です。すぐ見たいなら、`previews/offline_preview.html` をダブルクリックしてください（サーバー不要）。
