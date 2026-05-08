pipeline {
    agent any
    
    environment {
        // 你的私有镜像仓库地址
        HARBOR_URL = "172.16.10.76:80"
        // 你的镜像命名空间和名称
        IMAGE_NAME = "audit-project/backend"
        // 利用 Jenkins 自带的构建号生成动态版本标签 (如 v1.23)
        IMAGE_TAG = "v1.${BUILD_NUMBER}" 
    }

    stages {
        stage('1. 拉取最新代码') {
            steps {
                // 这个命令会自动拉取触发本次构建的 Git 分支代码
                checkout scm
            }
        }
        
        stage('2. 构建 Docker 镜像') {
            steps {
                echo "开始构建镜像: ${HARBOR_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
                sh "docker build -t ${HARBOR_URL}/${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }
        
        stage('3. 推送镜像到 Harbor') {
            steps {
                // 使用你在 Jenkins 里配置的凭证 ID (假设你起名叫 harbor-auth)
                withCredentials([usernamePassword(credentialsId: 'harbor-auth', passwordVariable: 'HARBOR_PWD', usernameVariable: 'HARBOR_USER')]) {
                    sh "docker login -u ${HARBOR_USER} -p ${HARBOR_PWD} ${HARBOR_URL}"
                    sh "docker push ${HARBOR_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }
        
        stage('4. 触发 K8s 自动更新') {
            steps {
                echo "通知 Kuboard 更新镜像版本..."
                // 【注意】这里必须替换为你真实的 Kuboard Webhook curl 命令
                sh """
                    curl -X PUT \
                    -H "Content-Type: application/yaml" \
                    -d '{"kind":"deployments","namespace":"default","name":"audit-backend","images":{"crpi-gi78lo9xue8grpmj.cn-shanghai.personal.cr.aliyuncs.com/ht-agent/audit-project-backend":"${HARBOR_URL}/${IMAGE_NAME}:${IMAGE_TAG}"}}' \
                    "https://172.16.10.76/kuboard-api/cluster/default/kind/CICDApi/admin/resource/updateImageTag"
                """
            }
        }
    }
}