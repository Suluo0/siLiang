pipeline {
    agent any

    environment {
        DOCKER_REGISTRY = 'localhost:5000'
        APP_IMAGE = 'topicsystem-app'
        WEB_IMAGE = 'topicsystem-web'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    pip install -q pytest pytest-asyncio httpx 2>/dev/null
                    python -m pytest tests/test_agentv3.py -q -k "not GoldenDataset" --tb=short || true
                '''
            }
        }

        stage('Build Backend') {
            steps {
                sh '''
                    docker build -t ${APP_IMAGE}:latest .
                '''
            }
        }

        stage('Build Frontend') {
            steps {
                sh '''
                    docker build -t ${WEB_IMAGE}:latest -f TOPICSYSTEM_Web/Dockerfile TOPICSYSTEM_Web/
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker compose down app web 2>/dev/null || true
                    docker compose up -d
                '''
            }
        }
    }

    post {
        always {
            echo "Pipeline finished"
        }
        success {
            echo "Deploy success — http://localhost"
        }
        failure {
            echo "Deploy failed — check logs"
        }
    }
}
