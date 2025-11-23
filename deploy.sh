#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install Docker Compose
sudo apt-get install -y docker-compose

# Setup .env if not exists
if [ ! -f backend/.env ]; then
    echo "Creating .env file..."
    read -p "Enter LLM API Key: " llm_key
    read -p "Enter ScrapingDog API Key: " scraping_key
    
    echo "LLM_API_KEY=$llm_key" > backend/.env
    echo "LLM_BASE_URL=https://api.openai.com/v1" >> backend/.env
    echo "LLM_MODEL=gpt-4o" >> backend/.env
    echo "SCRAPINGDOG_API_KEY=$scraping_key" >> backend/.env
fi

# Build and Run
echo "Building and starting services..."
sudo docker-compose up --build -d

echo "Deployment complete! Access the app at http://localhost:3000"
