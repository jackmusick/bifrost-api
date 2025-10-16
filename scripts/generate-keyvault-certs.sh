#!/bin/bash
# Generate self-signed certificates for Azure Key Vault Emulator
# Based on: https://github.com/james-gould/azure-keyvault-emulator

set -e

CERT_DIR="$(pwd)/keyvault-certs"
CERT_NAME="emulator"

echo "Creating certificate directory: $CERT_DIR"
mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for Key Vault emulator..."

# Generate private key (4096-bit to match official script)
openssl genrsa -out "$CERT_DIR/$CERT_NAME.key" 4096

# Generate certificate signing request
openssl req -new -key "$CERT_DIR/$CERT_NAME.key" -out "$CERT_DIR/$CERT_NAME.csr" -subj "/CN=keyvault/O=Development/C=US"

# Generate self-signed certificate (3560 days validity to match official script)
openssl x509 -req -days 3560 -in "$CERT_DIR/$CERT_NAME.csr" -signkey "$CERT_DIR/$CERT_NAME.key" -out "$CERT_DIR/$CERT_NAME.crt" -extfile <(printf "subjectAltName=DNS:keyvault,DNS:localhost,IP:127.0.0.1")

# Generate PFX file with password "emulator" (required by emulator)
openssl pkcs12 -export -out "$CERT_DIR/$CERT_NAME.pfx" -inkey "$CERT_DIR/$CERT_NAME.key" -in "$CERT_DIR/$CERT_NAME.crt" -passout pass:emulator

# Clean up CSR
rm "$CERT_DIR/$CERT_NAME.csr"

echo ""
echo "✅ Certificates generated successfully in $CERT_DIR"
echo ""
echo "Files created:"
echo "  - $CERT_NAME.key (private key)"
echo "  - $CERT_NAME.crt (certificate)"
echo "  - $CERT_NAME.pfx (PKCS#12 format for emulator)"
echo ""

# Detect OS and install certificate
OS="$(uname -s)"
case "$OS" in
    Darwin*)
        echo "📍 Detected: macOS"
        echo "Installing certificate to system trust store..."
        echo ""

        if sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CERT_DIR/$CERT_NAME.crt" 2>/dev/null; then
            echo "✅ Certificate installed and trusted successfully!"
        else
            echo "⚠️  Could not install certificate automatically (sudo required)"
            echo ""
            echo "Please run the following command to trust the certificate:"
            echo ""
            echo "  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/$CERT_NAME.crt"
            echo ""
        fi
        ;;

    Linux*)
        echo "📍 Detected: Linux"
        echo "Installing certificate to system trust store..."
        echo ""

        if sudo cp "$CERT_DIR/$CERT_NAME.crt" /usr/local/share/ca-certificates/ 2>/dev/null && sudo update-ca-certificates 2>/dev/null; then
            echo "✅ Certificate installed and trusted successfully!"
        else
            echo "⚠️  Could not install certificate automatically (sudo required)"
            echo ""
            echo "Please run the following commands to trust the certificate:"
            echo ""
            echo "  sudo cp $CERT_DIR/$CERT_NAME.crt /usr/local/share/ca-certificates/"
            echo "  sudo update-ca-certificates"
            echo ""
        fi
        ;;

    MINGW*|MSYS*|CYGWIN*)
        echo "📍 Detected: Windows (Git Bash/MSYS)"
        echo ""
        echo "⚠️  Manual installation required on Windows"
        echo ""
        echo "To trust the certificate:"
        echo "  1. Open certmgr.msc (Windows Certificate Manager)"
        echo "  2. Right-click 'Trusted Root Certification Authorities' > Certificates"
        echo "  3. Select 'All Tasks' > 'Import...'"
        echo "  4. Browse to: $CERT_DIR\\$CERT_NAME.crt"
        echo "  5. Complete the wizard"
        echo ""
        ;;

    *)
        echo "📍 Detected: Unknown OS ($OS)"
        echo ""
        echo "⚠️  Please manually install the certificate to your system's trust store"
        echo "Certificate location: $CERT_DIR/$CERT_NAME.crt"
        echo ""
        ;;
esac

echo ""
echo "Next step: Start Docker Compose"
echo "  docker-compose up --build"
echo ""
