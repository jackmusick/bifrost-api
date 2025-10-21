import { useState } from 'react';
import { useOrgScope } from '@/contexts/OrgScopeContext';
import { Skeleton } from '@/components/ui/skeleton';

interface LogoProps {
  type: 'square' | 'rectangle';
  className?: string;
  alt?: string;
}

/**
 * Logo component with automatic fallback to default logo
 * Uses preloaded logo URLs from OrgScopeContext (already fetched and cached)
 * For rectangle type: shows custom logo OR default icon + text
 * For square type: shows custom logo OR default icon only
 *
 * Shows skeleton loader while branding is being loaded
 */
export function Logo({ type, className = '', alt = 'Logo' }: LogoProps) {
  const { squareLogoUrl, rectangleLogoUrl, brandingLoaded, logoLoaded } = useOrgScope();
  const [error, setError] = useState(false);

  // Default logo - fallback to standard logo.svg
  const defaultLogo = '/logo.svg';

  // Get the logo URL from context based on type
  const logoUrl = type === 'square' ? squareLogoUrl : rectangleLogoUrl;

  const handleImageError = () => {
    console.error('Failed to load logo image, falling back to default');
    setError(true);
  };

  // Show skeleton while loading
  if (!brandingLoaded || !logoLoaded) {
    if (type === 'rectangle') {
      return (
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="hidden sm:block h-5 w-32 rounded" />
        </div>
      );
    }
    // Square skeleton - respect className if provided, otherwise use larger default
    return <Skeleton className={className || "h-10 w-10 rounded"} />;
  }

  // Show custom logo if available and no errors
  const hasCustomLogo = !error && logoUrl;

  if (hasCustomLogo) {
    // Custom branding - show logo only (parent container handles centering)
    // Image is already preloaded by OrgScopeContext
    return (
      <img
        src={logoUrl}
        alt={alt}
        className={className}
        onError={handleImageError}
      />
    );
  }

  // Default branding - show icon + text for rectangle, icon only for square
  if (type === 'rectangle') {
    return (
      <div className="flex items-center gap-2">
        <img src={defaultLogo} alt={alt} className="h-8 w-8" />
        <span className="hidden sm:inline-block font-semibold">
          Bifrost Integrations
        </span>
      </div>
    );
  }

  // Square type - just the icon
  return (
    <img
      src={defaultLogo}
      alt={alt}
      className={className}
    />
  );
}
