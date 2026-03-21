#!/bin/bash
# ═══════════════════════════════════════════════════
# Art&Auction — EC2 Deployment Script
# Run this ON the EC2 instance after SSH-ing in
# ═══════════════════════════════════════════════════

set -e

APP_DIR="/home/ubuntu/auction-management-system"
REPO_URL="https://github.com/aarushsai5/auction-management-system.git"

echo "═══════════════════════════════════════════"
echo "  Art&Auction — EC2 Setup"
echo "═══════════════════════════════════════════"

# 1. System updates
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
echo "[2/7] Installing Python, Nginx, Git..."
sudo apt install -y python3 python3-pip python3-venv nginx git

# 3. Clone repo (or pull latest)
if [ -d "$APP_DIR" ]; then
    echo "[3/7] Pulling latest code..."
    cd "$APP_DIR"
    git pull origin main
else
    echo "[3/7] Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# 4. Create virtual environment & install deps
echo "[4/7] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "[5/7] Creating .env file (EDIT THIS!)..."
    cat > .env <<EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=postgresql://user:password@your-db-host:5432/auction_db
EOF
    echo "⚠️  IMPORTANT: Edit .env with your actual DATABASE_URL!"
else
    echo "[5/7] .env already exists, skipping..."
fi

# 6. Setup systemd service
echo "[6/7] Configuring systemd service..."
sudo cp deploy/auction.service /etc/systemd/system/auction.service
sudo systemctl daemon-reload
sudo systemctl enable auction
sudo systemctl restart auction

# 7. Setup Nginx
echo "[7/7] Configuring Nginx..."
sudo cp deploy/nginx-auction.conf /etc/nginx/sites-available/auction
sudo ln -sf /etc/nginx/sites-available/auction /etc/nginx/sites-enabled/auction
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Deployment Complete!"
echo "═══════════════════════════════════════════"
echo ""
echo "  Your app is live at: http://$(curl -s ifconfig.me)"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status auction    # Check app status"
echo "    sudo journalctl -u auction -f    # View app logs"
echo "    sudo systemctl restart auction   # Restart app"
echo ""
