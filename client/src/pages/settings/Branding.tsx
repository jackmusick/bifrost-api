import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { Loader2, Upload, Palette } from 'lucide-react'
import { brandingService } from '@/services/branding'
import { applyBrandingTheme, type BrandingSettings } from '@/lib/branding'

export function Branding() {
  const [branding, setBranding] = useState<BrandingSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState<'square' | 'rectangle' | null>(null)
  const [primaryColor, setPrimaryColor] = useState('#0066CC')

  // Drag states
  const [dragActiveSquare, setDragActiveSquare] = useState(false)
  const [dragActiveRectangle, setDragActiveRectangle] = useState(false)

  // Load current branding
  useEffect(() => {
    async function loadBranding() {
      try {
        const data = await brandingService.getBranding()
        setBranding(data)
        if (data.primaryColor) {
          setPrimaryColor(data.primaryColor)
        }
      } catch (error) {
        console.error('Failed to load branding:', error)
        toast.error('Failed to load branding settings')
      } finally {
        setLoading(false)
      }
    }

    loadBranding()
  }, [])

  // Update primary color
  const handleColorUpdate = async () => {
    setSaving(true)
    try {
      const updated = await brandingService.updateBranding({ primaryColor })
      setBranding(updated)
      applyBrandingTheme(updated)

      toast.success('Branding updated', {
        description: 'Primary color has been updated successfully',
      })
    } catch (error) {
      console.error('Failed to update branding:', error)
      toast.error('Error', {
        description: error instanceof Error ? error.message : 'Failed to update branding',
      })
    } finally {
      setSaving(false)
    }
  }

  // Handle file upload
  const handleLogoUpload = useCallback(async (type: 'square' | 'rectangle', file: File) => {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Invalid file type', {
        description: 'Please upload an image file (PNG, JPG, or SVG)',
      })
      return
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File too large', {
        description: 'Please upload an image smaller than 5MB',
      })
      return
    }

    setUploading(type)
    try {
      await brandingService.uploadLogo(type, file)

      // Reload branding to get updated logo URL
      const updated = await brandingService.getBranding()
      setBranding(updated)
      applyBrandingTheme(updated)

      toast.success('Logo uploaded', {
        description: `${type === 'square' ? 'Square' : 'Rectangle'} logo has been updated successfully`,
      })
    } catch (error) {
      console.error('Failed to upload logo:', error)
      toast.error('Error', {
        description: error instanceof Error ? error.message : 'Failed to upload logo',
      })
    } finally {
      setUploading(null)
    }
  }, [])

  // Drag and drop handlers
  const handleDrag = useCallback((e: React.DragEvent, type: 'square' | 'rectangle') => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      if (type === 'square') setDragActiveSquare(true)
      else setDragActiveRectangle(true)
    } else if (e.type === 'dragleave') {
      if (type === 'square') setDragActiveSquare(false)
      else setDragActiveRectangle(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, type: 'square' | 'rectangle') => {
    e.preventDefault()
    e.stopPropagation()
    if (type === 'square') setDragActiveSquare(false)
    else setDragActiveRectangle(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleLogoUpload(type, e.dataTransfer.files[0])
    }
  }, [handleLogoUpload])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'square' | 'rectangle') => {
    const file = e.target.files?.[0]
    if (file) {
      handleLogoUpload(type, file)
    }
  }, [handleLogoUpload])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Primary Color */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Primary Color
          </CardTitle>
          <CardDescription>
            Choose your organization's primary brand color
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div>
              <Label htmlFor="primaryColor">Color (Hex)</Label>
              <Input
                id="primaryColor"
                type="text"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                placeholder="#0066CC"
                className="w-32 font-mono"
              />
            </div>
            <div>
              <Label>Preview</Label>
              <div
                className="h-10 w-20 rounded border"
                style={{ backgroundColor: primaryColor }}
              />
            </div>
          </div>
          <Button onClick={handleColorUpdate} disabled={saving} variant="default">
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Update Color
          </Button>
        </CardContent>
      </Card>

      {/* Logos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Brand Logos
          </CardTitle>
          <CardDescription>
            Upload logos for your organization (PNG, JPG, or SVG, max 5MB)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Square Logo */}
            <div className="space-y-3">
              <Label>Square Logo (1:1 ratio)</Label>
              <div
                className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
                  dragActiveSquare ? 'border-primary bg-primary/5' : 'border-border'
                } ${uploading === 'square' ? 'opacity-50 pointer-events-none' : 'cursor-pointer hover:border-primary/50'}`}
                onDragEnter={(e) => handleDrag(e, 'square')}
                onDragLeave={(e) => handleDrag(e, 'square')}
                onDragOver={(e) => handleDrag(e, 'square')}
                onDrop={(e) => handleDrop(e, 'square')}
                onClick={() => document.getElementById('squareLogoInput')?.click()}
              >
                <input
                  id="squareLogoInput"
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml"
                  onChange={(e) => handleFileInput(e, 'square')}
                  className="hidden"
                />
                {branding?.squareLogoUrl ? (
                  <div className="flex flex-col items-center gap-3">
                    <img
                      src={branding.squareLogoUrl}
                      alt="Square logo"
                      className="h-24 w-24 object-contain"
                    />
                    <p className="text-xs text-muted-foreground">Click or drag to replace</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-center">
                    <Upload className="h-10 w-10 text-muted-foreground" />
                    <p className="text-sm font-medium">Drop square logo here</p>
                    <p className="text-xs text-muted-foreground">or click to browse</p>
                  </div>
                )}
                {uploading === 'square' && (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
                    <Loader2 className="h-8 w-8 animate-spin" />
                  </div>
                )}
              </div>
            </div>

            {/* Rectangle Logo */}
            <div className="space-y-3">
              <Label>Rectangle Logo (16:9 ratio)</Label>
              <div
                className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
                  dragActiveRectangle ? 'border-primary bg-primary/5' : 'border-border'
                } ${uploading === 'rectangle' ? 'opacity-50 pointer-events-none' : 'cursor-pointer hover:border-primary/50'}`}
                onDragEnter={(e) => handleDrag(e, 'rectangle')}
                onDragLeave={(e) => handleDrag(e, 'rectangle')}
                onDragOver={(e) => handleDrag(e, 'rectangle')}
                onDrop={(e) => handleDrop(e, 'rectangle')}
                onClick={() => document.getElementById('rectangleLogoInput')?.click()}
              >
                <input
                  id="rectangleLogoInput"
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml"
                  onChange={(e) => handleFileInput(e, 'rectangle')}
                  className="hidden"
                />
                {branding?.rectangleLogoUrl ? (
                  <div className="flex flex-col items-center gap-3">
                    <img
                      src={branding.rectangleLogoUrl}
                      alt="Rectangle logo"
                      className="h-12 w-48 object-contain"
                    />
                    <p className="text-xs text-muted-foreground">Click or drag to replace</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-center">
                    <Upload className="h-10 w-10 text-muted-foreground" />
                    <p className="text-sm font-medium">Drop rectangle logo here</p>
                    <p className="text-xs text-muted-foreground">or click to browse</p>
                  </div>
                )}
                {uploading === 'rectangle' && (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
                    <Loader2 className="h-8 w-8 animate-spin" />
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
