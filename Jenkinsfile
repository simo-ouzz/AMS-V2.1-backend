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
          docker compose -f docker-compose.prod.yml up -d --build
        '''
      }
    }
  }
}
