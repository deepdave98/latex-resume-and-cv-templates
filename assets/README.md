# Social preview

`social-preview.html` uses the published template images. Render it at 1280 × 640 to update `social-preview.png`:

```bash
cd tools/pdf-review
npm ci --ignore-scripts
npx playwright install chromium
npx playwright screenshot --viewport-size="1280,640" ../../assets/social-preview.html ../../assets/social-preview.png
```

Check the image, then upload it under the repository's **Settings → General → Social preview**. Committing the PNG does not update GitHub's selected image.
