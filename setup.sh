#!/bin/bash

# UAV Log Viewer with AI Assistant - Setup Script
# Arena AI Take-Home Challenge

echo "🚀 Setting up UAV Log Viewer with AI Assistant..."
echo "=================================================="

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
npm install

# Install backend dependencies
echo "🐍 Installing backend dependencies..."
cd backend
pip3 install -r requirements.txt
cd ..

# Create environment file template
echo "🔧 Creating environment template..."
cat > backend/.env.template << 'EOF'
# OpenAI API Key (primary)
OPENAI_API_KEY=your_openai_key_here

# Anthropic API Key (fallback)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional: Development settings
DEBUG=true
LOG_LEVEL=info
EOF

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Copy backend/.env.template to backend/.env"
echo "2. Add your OpenAI and Anthropic API keys to backend/.env"
echo "3. Start the backend: cd backend && python3 app.py"
echo "4. Start the frontend: npm run dev"
echo "5. Open http://localhost:8080 in your browser"
echo ""
echo "🎯 Ready for Arena AI submission!"