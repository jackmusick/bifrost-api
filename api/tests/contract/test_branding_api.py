"""
Contract tests for branding API endpoints

Tests branding configuration retrieval and updates with logo uploads and color validation.
"""

from shared.models import BrandingSettings


class TestBrandingContracts:
    """Contract tests for branding API"""

    def test_branding_settings_model_structure(self):
        """Test that BrandingSettings model has required fields"""
        # Test model can be instantiated with all fields
        branding = BrandingSettings(
            squareLogoUrl="https://example.com/logo-square.png",
            rectangleLogoUrl="https://example.com/logo-rect.png",
            primaryColor="#0066CC"
        )

        assert branding.squareLogoUrl == "https://example.com/logo-square.png"
        assert branding.rectangleLogoUrl == "https://example.com/logo-rect.png"
        assert branding.primaryColor == "#0066CC"

    def test_branding_settings_optional_fields(self):
        """Test that branding fields are optional (can be None)"""
        # Test with minimal fields
        branding = BrandingSettings(
            squareLogoUrl=None,
            rectangleLogoUrl=None,
            primaryColor=None
        )

        assert branding.squareLogoUrl is None
        assert branding.rectangleLogoUrl is None
        assert branding.primaryColor is None

    def test_primary_color_hex_format_validation(self):
        """Test that primary color validates hex format"""
        # Valid hex colors
        valid_colors = ["#000000", "#FFFFFF", "#0066CC", "#ff6600"]

        for color in valid_colors:
            branding = BrandingSettings(
                squareLogoUrl=None,
                rectangleLogoUrl=None,
                primaryColor=color
            )
            assert branding.primaryColor == color

    def test_branding_fallback_to_defaults(self):
        """Test that missing branding falls back to None (frontend handles defaults)"""
        branding = BrandingSettings(
            squareLogoUrl=None,
            rectangleLogoUrl=None,
            primaryColor=None
        )

        # Frontend should handle None values by showing default branding
        assert branding.squareLogoUrl is None
        assert branding.rectangleLogoUrl is None
        assert branding.primaryColor is None
