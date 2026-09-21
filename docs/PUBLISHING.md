# Publishing the shorts

`factory export --video out/x.mp4 --script script.json` writes one folder per platform:

```
out/x/export/
  youtube/   video.mp4  meta.json            # title, caption with #Shorts, warnings
  instagram/ video.mp4  meta.json
  tiktok/    video.mp4  meta.json            # warns when the master is under 60 s
  facebook/  video.mp4  meta.json            # trimmed to 90 s if longer
  snapchat/  video.mp4  meta.json            # trimmed to 60 s if longer
  reddit/    video.mp4  meta.json  post.md   # text post + suggested subreddits
```

`meta.json` carries `title`, `caption`, `hashtags`, `seconds`, `trimmed`, `warnings` and the
platform's `safe_zone` (fractions of the frame that UI covers). The master render already keeps
captions in the centre and the title card below the top 14 %, so no re-layout is needed.

## Per-platform limits baked into `factory.platforms`

| Platform | Max | Monetisation floor | Title | Caption | Tags | Notes |
|---|---|---|---|---|---|---|
| YouTube Shorts | 180 s | – | 100 | 5000 | 3 (+`#Shorts`) | July 2025 inauthentic-content policy: add a creator layer before scaling |
| Instagram Reels | 180 s | – | – | 2200 | 5 | first caption line is the hook |
| TikTok | 600 s | 60 s (Creator Rewards) | – | 4000 | 4 | caption is searchable text |
| Facebook Reels | 90 s | – | – | 2200 | 3 | >90 s posts as normal video |
| Snapchat Spotlight | 60 s | – | – | 160 | 2 | one-line description |
| Reddit | 900 s | – | 300 | text body | 0 | story subs are text-first |

Update the numbers in `PLATFORMS` when a platform changes its limits; the tests only check
internal consistency, not the live values.

## Uploading

Start on YouTube (the user's first target), then fan out. Every platform below has an
official upload API; none is wired into the factory yet, so the export folder is the
hand-off point. When automating, keep one master per story and upload the platform copy,
never re-encode per platform beyond the trim the export already did.

- **YouTube** — YouTube Data API v3 `videos.insert` (resumable upload) with `snippet.title`,
  `snippet.description` (caption), `snippet.tags`, `status.privacyStatus`, and
  `status.selfDeclaredMadeForKids=false`. A 9:16 video ≤ 3 min is classified as a Short
  automatically; `#Shorts` in the title or description helps the feed. Quota: 1,600 units
  per upload against a default 10,000/day, i.e. 6 uploads/day unless quota is raised.
- **Instagram Reels** — Instagram Graph API for professional accounts: `POST /{ig-user-id}/media`
  with `media_type=REELS`, `video_url` (must be a public https URL), `caption`, then
  `POST /{ig-user-id}/media_publish`. Poll `status_code` on the container until `FINISHED`.
- **TikTok** — Content Posting API (`/v2/post/publish/video/init/` with `FILE_UPLOAD` or
  `PULL_FROM_URL`), needs the `video.publish` scope and an audited app; unaudited apps can only
  post privately. Title (caption) goes in `post_info.title`; hashtags are plain `#tag` text.
- **Facebook Reels** — Pages API: `POST /{page-id}/video_reels` (`upload_phase=start`), upload
  bytes to the returned URL, then `upload_phase=finish` with `description` and
  `video_state=PUBLISHED`. Needs `pages_manage_posts` + `pages_read_engagement`.
- **Snapchat** — No public upload API for Spotlight; use the Snapchat app or Creator Hub on
  desktop. Public Profile posting via the Marketing API is ads-only.
- **Reddit** — Data API `POST /api/submit` with `kind=video` needs the media-asset upload flow
  (`/api/media/asset.json` → S3 → `video_poster_url`); for story subs submit `kind=self` with
  `post.md`'s title and body instead. Check each subreddit's rules on self-promotion and AI
  narration first.

Third-party schedulers (Buffer, Metricool, Publer, Later) cover YouTube, Instagram, TikTok
and Facebook from one upload and are the quickest path to 2 posts/day across platforms
before the direct integrations exist.

## Cadence and the policy layer

- Post the same short to all platforms within the same hour; the story's newness is the hook.
- TikTok: a ≥60 s cut (extended script, not padding) is the one that earns; keep both.
- YouTube: mass-produced narration-over-stock is the exact pattern the 2025 policy targets.
  Roadmap item: a creator verdict/commentary overlay on the last 5 s and in the description.
