# GitHub Release 公開手順

CAS の GitHub Release を tag から作成するチェックリストです。

## 対象リリース

| Tag | 本文 | タイトル例 |
|-----|------|-----------|
| `v1.9.0` | [`RELEASE_NOTES_v1.9.0.md`](RELEASE_NOTES_v1.9.0.md) | CAS v1.9.0 — Phase 10B |
| `v1.8.0` | [`RELEASE_NOTES_v1.8.0.md`](RELEASE_NOTES_v1.8.0.md) | CAS v1.8.0 — Phase 10A |
| `v1.7.0` | [`RELEASE_NOTES_v1.7.0.md`](RELEASE_NOTES_v1.7.0.md) | CAS v1.7.0 — Phase 9E |
| `v1.6.0` | [`RELEASE_NOTES_v1.6.0.md`](RELEASE_NOTES_v1.6.0.md) | CAS v1.6.0 — Phase 9D |
| `v1.5.0` | [`RELEASE_NOTES_v1.5.0.md`](RELEASE_NOTES_v1.5.0.md) | CAS v1.5.0 — Phase 9C |
| `v1.4.0` | [`RELEASE_NOTES_v1.4.0.md`](RELEASE_NOTES_v1.4.0.md) | CAS v1.4.0 — Phase 9B |
| `v1.3.0` | [`RELEASE_NOTES_v1.3.0.md`](RELEASE_NOTES_v1.3.0.md) | CAS v1.3.0 — Phase 9A |
| `v1.2.2` | [`RELEASE_NOTES_v1.2.2.md`](RELEASE_NOTES_v1.2.2.md) | CAS v1.2.2 — Phase 8B |
| `v1.2.1` | [`RELEASE_NOTES_v1.2.1.md`](RELEASE_NOTES_v1.2.1.md) | CAS v1.2.1 — Phase 8 |
| `v1.2.0` | [`RELEASE_NOTES_v1.2.0.md`](RELEASE_NOTES_v1.2.0.md) | CAS v1.2.0 — Phase 7 |
| `v1.1.0` | [`RELEASE_NOTES_v1.1.0.md`](RELEASE_NOTES_v1.1.0.md) | CAS v1.1.0 — Phase 5 |
| `v1.0.0` | [`RELEASE_NOTES_v1.0.0.md`](RELEASE_NOTES_v1.0.0.md) | CAS v1.0.0 — Phase 4 complete |

---

## 事前確認

- [ ] `git fetch --tags` で remote tag を確認
- [ ] `main` に Phase 6A ドキュメントが push 済み（Release 本文の raw 画像 URL が有効）
- [ ] ローカルで `pytest tests/` が PASS

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
git fetch --tags
git tag -l "v1.*"
```

---

## v1.2.2 Release 作成

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
git tag v1.2.2
git push origin v1.2.2
gh release create v1.2.2 --title "CAS v1.2.2 — Phase 8B" --notes-file docs/RELEASE_NOTES_v1.2.2.md
```

既に Release がある場合:

```powershell
gh release edit v1.2.2 --title "CAS v1.2.2 — Phase 8B" --notes-file docs/RELEASE_NOTES_v1.2.2.md
```

---

## v1.2.1 Release 作成

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
git tag v1.2.1
git push origin v1.2.1
gh release create v1.2.1 --title "CAS v1.2.1 — Phase 8" --notes-file docs/RELEASE_NOTES_v1.2.1.md
```

既に Release がある場合:

```powershell
gh release edit v1.2.1 --title "CAS v1.2.1 — Phase 8" --notes-file docs/RELEASE_NOTES_v1.2.1.md
```

---

## v1.2.0 Release 作成

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
git tag v1.2.0
git push origin v1.2.0
gh release create v1.2.0 --title "CAS v1.2.0 — Phase 7" --notes-file docs/RELEASE_NOTES_v1.2.0.md
```

既に Release がある場合:

```powershell
gh release edit v1.2.0 --title "CAS v1.2.0 — Phase 7" --notes-file docs/RELEASE_NOTES_v1.2.0.md
```

---

## v1.1.0 Release 作成

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
gh release create v1.1.0 --title "CAS v1.1.0 — Phase 5" --notes-file docs/RELEASE_NOTES_v1.1.0.md
```

既に Release がある場合（再作成）:

```powershell
gh release edit v1.1.0 --title "CAS v1.1.0 — Phase 5" --notes-file docs/RELEASE_NOTES_v1.1.0.md
```

---

## v1.0.0 Release（未作成の場合のみ）

tag は push 済みだが Release ページが無い場合:

```powershell
gh release create v1.0.0 --title "CAS v1.0.0 — Phase 4 complete" --notes-file docs/RELEASE_NOTES_v1.0.0.md
```

---

## 公開後確認

- [ ] https://github.com/maouM-cmd/conjunction-alert-simulator/releases/tag/v1.1.0 が開ける
- [ ] Release 本文に demo.gif（raw URL）が表示される
- [ ] [`CHANGELOG.md`](../CHANGELOG.md) の `[1.1.0]` リンクが Release ページを指す
- [ ] README の Release バッジが `v1.1.0` を表示

```powershell
gh release view v1.1.0
```

---

## 関連

- [公開マスターチェックリスト v1.1.0](publish-checklist-v1.1.0.md)
- [Zenn 投稿手順](publish-zenn.md)
