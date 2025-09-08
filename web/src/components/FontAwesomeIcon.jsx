// React import not needed in React 17+

/**
 * Font Awesome Free Icon Component
 * 
 * Uses Font Awesome Free 6 icons
 * Supports: solid, regular, brands styles
 * 
 * @param {string} icon - Icon name (e.g., 'home', 'server', 'bell')
 * @param {string} style - Icon style: 'solid', 'regular', 'brands' (default: 'solid')
 * @param {string} className - Additional CSS classes
 * @param {string} size - Size classes: 'xs', 'sm', 'lg', '2x', '3x', '4x', '5x'
 * @param {boolean} spin - Spinning animation
 * @param {boolean} pulse - Pulse animation
 * @param {boolean} fixedWidth - Fixed width icon
 */
const FontAwesomeIcon = ({ 
  icon, 
  style = 'solid', 
  className = '', 
  size = null,
  spin = false,
  pulse = false,
  fixedWidth = false,
  ...props 
}) => {
  // Map style to Font Awesome prefix
  const styleMap = {
    solid: 'fas',
    regular: 'far',
    brands: 'fab'
  };

  const prefix = styleMap[style] || 'fas';
  
  // Build class list
  const classes = [
    prefix,
    `fa-${icon}`,
    size && `fa-${size}`,
    spin && 'fa-spin',
    pulse && 'fa-pulse',
    fixedWidth && 'fa-fw',
    className
  ].filter(Boolean).join(' ');

  return <i className={classes} {...props} />;
};

// Convenience components for each style
export const Icon = FontAwesomeIcon;
export const IconSolid = (props) => <FontAwesomeIcon {...props} style="solid" />;
export const IconRegular = (props) => <FontAwesomeIcon {...props} style="regular" />;
export const IconBrands = (props) => <FontAwesomeIcon {...props} style="brands" />;

// For backward compatibility with components expecting duotone/light
// These will use solid as fallback
export const IconDuotone = (props) => <FontAwesomeIcon {...props} style="solid" className={`${props.className || ''} opacity-90`} />;
export const IconLight = (props) => <FontAwesomeIcon {...props} style="regular" />;

export default FontAwesomeIcon;