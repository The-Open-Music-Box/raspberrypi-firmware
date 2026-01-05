// TheOpenMusicBox - Raspberry Pi Firmware Pipeline
// ================================================
// Equivalent to rpi-firmware/.github/workflows/ci.yml

pipeline {
    agent none

    environment {
        USE_MOCK_HARDWARE = 'true'
        ENVIRONMENT = 'test'
        PUSHGATEWAY_URL = 'http://pushgateway:9091'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
        ansiColor('xterm')
        skipDefaultCheckout()
    }

    triggers {
        githubPush()
    }

    stages {
        stage('Check Rebase') {
            agent { label 'python' }
            when {
                changeRequest()
            }
            steps {
                checkout scm

                sh '''
                    echo "=== Checking if rebased on develop ==="
                    git fetch origin develop

                    MERGE_BASE=$(git merge-base HEAD origin/develop)
                    DEVELOP_HEAD=$(git rev-parse origin/develop)

                    if [ "$MERGE_BASE" != "$DEVELOP_HEAD" ]; then
                        echo "Branch is not rebased on develop. Please rebase your branch."
                        echo ""
                        echo "Run the following commands:"
                        echo "  git fetch origin develop"
                        echo "  git rebase origin/develop"
                        echo "  git push --force-with-lease"
                        exit 1
                    fi

                    echo "Branch is up to date with develop"
                '''
            }
        }

        stage('Backend Tests') {
            agent { label 'python' }
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: scm.branches,
                    extensions: [[$class: 'SubmoduleOption', recursiveSubmodules: true]],
                    userRemoteConfigs: scm.userRemoteConfigs
                ])

                dir('back') {
                    sh '''
                        echo "=== Setting up Python virtual environment ==="
                        rm -rf venv
                        python3 -m venv venv
                        . venv/bin/activate
                        python -m pip install --upgrade pip
                    '''

                    sh '''
                        echo "=== Installing dependencies ==="
                        . venv/bin/activate
                        pip install -r requirements.txt
                        pip install -r requirements-test.txt
                    '''

                    sh '''
                        echo "=== Running unit tests ==="
                        . venv/bin/activate
                        pytest tests/unit/ -v --tb=short --junitxml=test-results-unit.xml
                    '''

                    sh '''
                        echo "=== Running contract tests ==="
                        . venv/bin/activate
                        pytest tests/contracts/ -v --tb=short --junitxml=test-results-contracts.xml
                    '''

                    sh '''
                        echo "=== Running integration tests ==="
                        . venv/bin/activate
                        pytest tests/integration/ -v --tb=short --junitxml=test-results-integration.xml
                    '''
                }
            }
            post {
                always {
                    junit 'back/test-results-*.xml'
                    cleanWs()
                }
            }
        }

        stage('Frontend Tests') {
            agent { label 'python' }
            steps {
                checkout scm

                dir('front') {
                    sh '''
                        echo "=== Installing dependencies ==="
                        npm ci
                    '''

                    sh '''
                        echo "=== Running tests ==="
                        npm run test:unit
                    '''
                }
            }
            post {
                always {
                    cleanWs()
                }
            }
        }

        stage('Build Test') {
            agent { label 'python' }
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: scm.branches,
                    extensions: [[$class: 'SubmoduleOption', recursiveSubmodules: true]],
                    userRemoteConfigs: scm.userRemoteConfigs
                ])

                dir('front') {
                    sh '''
                        echo "=== Building frontend ==="
                        npm ci
                        npm run build
                    '''

                    sh '''
                        echo "=== Verifying build output ==="
                        if [ ! -d "dist" ]; then
                            echo "Build failed - dist directory not found"
                            exit 1
                        fi
                        echo "Build successful"
                        ls -la dist/
                    '''
                }
            }
            post {
                always {
                    cleanWs()
                }
            }
        }

        stage('CI Status') {
            agent { label 'python' }
            steps {
                script {
                    echo "Pipeline Status: ${currentBuild.result ?: 'SUCCESS'}"

                    if (currentBuild.result != null && currentBuild.result != 'SUCCESS') {
                        error "CI checks failed"
                    }

                    echo "All CI checks passed!"
                }
            }
        }
    }

    post {
        always {
            node('python') {
                script {
                    def buildSuccess = currentBuild.result == 'SUCCESS' ? 1 : 0
                    def branchName = env.BRANCH_NAME ?: 'unknown'

                    sh """
                        cat <<EOF | curl --data-binary @- ${PUSHGATEWAY_URL}/metrics/job/ci/instance/rpi-firmware || true
ci_tests_success{repo="raspberrypi-firmware",branch="${branchName}"} ${buildSuccess}
ci_build_timestamp{repo="raspberrypi-firmware",branch="${branchName}"} \$(date +%s)
EOF
                    """
                }
            }
        }
        success {
            echo 'RPI Firmware CI passed!'
        }
        failure {
            echo 'RPI Firmware CI failed!'
        }
    }
}
