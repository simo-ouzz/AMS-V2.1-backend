pipeline {
  agent any
  options { timestamps() }
  stages {
    stage('Pull') {
      steps {
        sh '''
          cd /opt/AMS-V2.2/AMS-V2.1-backend
          git pull origin main
        '''
      }
    }
    stage('Deploy') {
      steps {
        sh '''
          cd /opt/AMS-V2.2/AMS-V2.1-backend
          # cp -f .env.prod .env
          # Set this to your separate frontend repo absolute path on the server.
          export FRONTEND_BUILD_CONTEXT=/opt/AMS-V2.2/AMS-V2.1-frontend
          docker compose -f docker-compose.prod.yml up -d --build
        '''
      }
    }
  }
}
