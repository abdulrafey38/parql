# ParQL Documentation

This directory contains the comprehensive documentation for ParQL, hosted on GitHub Pages.

## Structure

- `index.html` - Main documentation landing page with overview, features, and quick start guide
- `commands.html` - Complete command reference with examples for all ParQL commands
- `styles.css` - Modern, responsive CSS styling for the documentation site
- `script.js` - Interactive JavaScript functionality for the documentation

## Features

- **Modern Design** - Beautiful, responsive UI with smooth animations
- **Interactive Elements** - Tabbed examples, copy-to-clipboard functionality, smooth scrolling
- **Mobile Responsive** - Optimized for all device sizes
- **Syntax Highlighting** - Code examples with proper syntax highlighting
- **Search & Navigation** - Easy navigation between sections and commands

## Deployment

The documentation is automatically deployed to GitHub Pages using GitHub Actions. The workflow is configured in `.github/workflows/deploy.yml`.

### Manual Deployment

To manually deploy the documentation:

1. Ensure all files are in the `docs/` directory
2. Push to the main branch
3. GitHub Actions will automatically build and deploy to the `gh-pages` branch
4. The site will be available at `https://[username].github.io/parql/`

## Local Development

To run the documentation locally:

1. Clone the repository
2. Navigate to the `docs/` directory
3. Open `index.html` in a web browser
4. Or use a local server:
   ```bash
   cd docs
   python -m http.server 8000
   # Then visit http://localhost:8000
   ```

## Documentation Sections

### Main Page (`index.html`)
- Hero section with terminal demo
- Feature overview
- Quick start guide
- Command categories
- Interactive examples
- API reference

### Commands Reference (`commands.html`)
- Complete command documentation
- Examples for each command
- Options and parameters
- Organized by category:
  - Basic Operations
  - Analytics & Aggregation
  - Data Processing
  - Visualization
  - Data Quality
  - System Commands

## Styling

The documentation uses a modern design system with:
- CSS custom properties for consistent theming
- Inter font family for excellent readability
- Smooth animations and transitions
- Dark mode code blocks
- Responsive grid layouts

## JavaScript Features

- Mobile navigation toggle
- Smooth scrolling navigation
- Tab functionality for examples
- Copy-to-clipboard for code blocks
- Intersection Observer for animations
- Keyboard shortcuts
- Performance optimizations

## Contributing

To update the documentation:

1. Edit the HTML files in the `docs/` directory
2. Update CSS styles in `styles.css` if needed
3. Add JavaScript functionality in `script.js`
4. Test locally before pushing
5. Push changes to trigger automatic deployment

## Browser Support

The documentation supports all modern browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance

The documentation is optimized for performance:
- Minimal external dependencies
- Optimized images and assets
- Efficient CSS and JavaScript
- Lazy loading where appropriate
- Compressed and minified assets
