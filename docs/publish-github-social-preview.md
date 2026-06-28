# GitHub Social Preview 設定

リポジトリを SNS / Slack 等でシェアした際の OGP 画像（Social Preview）設定手順です。

**素材:** [`.github/social-preview.png`](../.github/social-preview.png)（`02-conjunctions.png` ベース）

**設定済み（Phase 6F）:** `repository-images.githubusercontent.com` にホストされた OGP 画像。

---

## 設定手順

1. https://github.com/maouM-cmd/conjunction-alert-simulator を開く
2. 右上 **⚙️ About** → **Edit repository details**
3. **Social preview** → **Upload an image...**
4. [`.github/social-preview.png`](../.github/social-preview.png) を選択してアップロード
5. **Save changes**

推奨サイズ: **1280×640** px（GitHub が自動 crop する場合あり）

---

## 確認

- リポ URL を X / Slack 等に貼り付け、プレビュー画像が表示されることを確認
- CLI 確認（設定前は GitHub デフォルト OGP）:

```powershell
gh api graphql -f query='query { repository(owner:"maouM-cmd", name:"conjunction-alert-simulator") { openGraphImageUrl } }' --jq .data.repository.openGraphImageUrl
```

カスタム画像反映後、`opengraph.githubassets.com` 以外の URL になる場合があります。

---

## 関連

- [GitHub About 設定](publish-github-about.md)
- [公開チェックリスト v1.1.0](publish-checklist-v1.1.0.md)
