# Web Assets Directory

Place your web assets (logos, favicons) in this directory. They will be served by the web interface.

## Required Files

Place the following files in this directory:

### Favicons
- `favicon.ico` - Traditional favicon (16x16, 32x32, or multi-resolution)
- `favicon.png` - Modern favicon (32x32 or 64x64 PNG)

### Logos
- `logo.png` - Main application logo (recommended: 512x512)
- `logo-192.png` - PWA icon medium (192x192)
- `logo-512.png` - PWA icon large (512x512)

### Optional Assets
- `logo.svg` - Vector logo for scalability
- `apple-touch-icon.png` - Apple devices (180x180)
- `og-image.png` - Open Graph preview (1200x630)

## File Structure
```
web/public/
├── favicon.ico       # Multi-resolution ICO
├── favicon.png       # 32x32 or 64x64 PNG
├── logo.png         # Main logo (512x512)
├── logo-192.png     # PWA medium icon
├── logo-512.png     # PWA large icon
└── README.md        # This file
```

## Docker Volume Mount

To use custom assets in Docker, uncomment this line in docker-compose.yml:
```yaml
volumes:
  - ./web/public:/app/web/dist/assets:ro
```

## Design Guidelines

- Use transparent backgrounds for logos when possible
- Maintain the Jellyfin purple gradient theme (#aa5cc3 → #7f86ff → #00a4dc)
- Ensure icons are crisp at their target resolutions
- Test favicons in multiple browsers

## Image Optimization

Before deploying, optimize your images:
```bash
# PNG optimization
optipng -o7 *.png

# Or using imagemin
npx imagemin *.png --out-dir=optimized/
```

## Notes

- The web interface will use these assets automatically
- Changes require a container restart to take effect
- Assets are served from `/assets/` path in the web interface