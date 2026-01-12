// TheOpenMusicBox - Raspberry Pi Firmware Pipeline
// ================================================
// CI/CD Pipeline with Prometheus metrics export

pipeline {
    agent none

    environment {
        USE_MOCK_HARDWARE = 'true'
        ENVIRONMENT = 'test'
        PUSHGATEWAY_URL = 'http://pushgateway:9091'
        REPO_NAME = 'rpi-firmware'
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
                        echo "=== Running unit tests with coverage ==="
                        . venv/bin/activate
                        pytest tests/unit/ -v --tb=short --junitxml=test-results-unit.xml --cov=. --cov-report=term 2>&1 | tee test_output.txt
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

                    // Parse test results and coverage
                    script {
                        def testOutput = readFile('test_output.txt')
                        def testsTotal = 0
                        def testsPassed = 0
                        def coveragePercent = 0

                        // Parse pytest output for test counts
                        def matcher = testOutput =~ /(\d+) passed/
                        if (matcher.find()) {
                            testsPassed = matcher[0][1].toInteger()
                        }
                        matcher = testOutput =~ /(\d+) failed/
                        def testsFailed = 0
                        if (matcher.find()) {
                            testsFailed = matcher[0][1].toInteger()
                        }
                        testsTotal = testsPassed + testsFailed

                        // Parse coverage percentage (TOTAL line from pytest-cov)
                        matcher = testOutput =~ /TOTAL\s+\d+\s+\d+\s+(\d+)%/
                        if (matcher.find()) {
                            coveragePercent = matcher[0][1].toInteger()
                        }

                        env.TESTS_TOTAL = testsTotal.toString()
                        env.TESTS_PASSED = testsPassed.toString()
                        env.COVERAGE_PERCENT = coveragePercent.toString()
                    }
                }
            }
            post {
                always {
                    junit 'back/test-results-*.xml'

                    // Export test metrics
                    script {
                        def branchName = env.BRANCH_NAME ?: 'unknown'
                        def coveragePercent = env.COVERAGE_PERCENT ?: '0'
                        def testsTotal = env.TESTS_TOTAL ?: '0'
                        def testsPassed = env.TESTS_PASSED ?: '0'

                        sh """
                            cat <<EOF | curl --data-binary @- ${PUSHGATEWAY_URL}/metrics/job/ci-tests/instance/${REPO_NAME} || true
ci_test_coverage_percent{repo="${REPO_NAME}",branch="${branchName}"} ${coveragePercent}
ci_tests_total{repo="${REPO_NAME}",branch="${branchName}"} ${testsTotal}
ci_tests_passed{repo="${REPO_NAME}",branch="${branchName}"} ${testsPassed}
EOF
                        """
                    }

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
                    def buildDuration = currentBuild.duration / 1000 // Convert ms to seconds

                    sh """
                        cat <<EOF | curl --data-binary @- ${PUSHGATEWAY_URL}/metrics/job/ci/instance/${REPO_NAME} || true
ci_tests_success{repo="${REPO_NAME}",branch="${branchName}"} ${buildSuccess}
ci_build_duration_seconds{repo="${REPO_NAME}",branch="${branchName}"} ${buildDuration}
ci_build_timestamp{repo="${REPO_NAME}",branch="${branchName}"} \$(date +%s)
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
