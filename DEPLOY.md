# 植物大战僵尸 PvP 多人对战 — 部署指南

## 前置条件

- 一台 Linux 云服务器（推荐：阿里云 ECS / 腾讯云轻量服务器）
  - CPU: 2 vCPU
  - 内存: 2 GB
  - 操作系统: Ubuntu 20.04+ 或 CentOS 7+
- Python 3.7+
- 公网 IP

## 第一步：服务器环境配置

### Ubuntu/Debian

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3 和 pip
sudo apt install -y python3 python3-pip git

# 检查版本
python3 --version  # 应为 3.7+
```

### CentOS/RHEL

```bash
sudo yum install -y python3 python3-pip git
python3 --version
```

## 第二步：部署游戏服务器

```bash
# 克隆仓库
cd /opt
git clone https://github.com/yourusername/PythonPlantsVsZombies.git
cd PythonPlantsVsZombies

# 安装依赖（服务器不需要 pygame，但安装也无妨）
pip3 install websockets
```

## 第三步：配置防火墙

```bash
# 开放 WebSocket 端口（默认 8765）

# Ubuntu (ufw)
sudo ufw allow 8765/tcp
sudo ufw enable

# 阿里云 ECS / 腾讯云
# 请在云控制台安全组中添加入站规则：
#   协议: TCP
#   端口: 8765
#   来源: 0.0.0.0/0
```

## 第四步：启动服务器

```bash
# 直接启动（前台运行，测试用）
cd /opt/PythonPlantsVsZombies
python3 -m source.network.server --host 0.0.0.0 --port 8765

# 后台运行
nohup python3 -m source.network.server --host 0.0.0.0 --port 8765 > server.log 2>&1 &
```

## 第五步：配置 systemd 服务（开机自启）

```bash
sudo tee /etc/systemd/system/pvz-server.service << 'EOF'
[Unit]
Description=Plants vs Zombies PvP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/PythonPlantsVsZombies
ExecStart=/usr/bin/python3 -m source.network.server --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 启动并启用
sudo systemctl daemon-reload
sudo systemctl start pvz-server
sudo systemctl enable pvz-server

# 查看状态
sudo systemctl status pvz-server

# 查看日志
sudo journalctl -u pvz-server -f
```

## 第六步：客户端连接

1. 启动游戏客户端: `python main.py`
2. 在主菜单点击 **"多人对战"**
3. 输入服务器公网 IP 和端口（如 `123.45.67.89:8765`）
4. 点击 **"连接服务器"**
5. 点击 **"快速匹配"** 或输入房间号 **"加入房间"**
6. 等待对手加入 → 点击 **"准备好了!"**
7. 开始对战！

## 故障排查

### 检查服务器是否在运行
```bash
ps aux | grep "source.network.server"
```

### 检查端口是否开放
```bash
# 服务器上
ss -tlnp | grep 8765

# 客户端上测试连通性
telnet <服务器IP> 8765
```

### 查看服务器日志
```bash
# 如果用 systemd
sudo journalctl -u pvz-server -n 50

# 如果用 nohup
tail -f /opt/PythonPlantsVsZombies/server.log
```

## 性能参考

- 内存占用: 约 50-100 MB
- CPU 占用: 每个房间约 1-2% CPU
- 支持并发房间: 2 vCPU/2GB 约可支持 20-50 个房间

## 注意事项

1. 服务器代码不依赖 Pygame，可在纯命令行 Linux 环境运行
2. 客户端仍需安装 Pygame 来渲染画面
3. 默认端口 8765 可按需修改（修改 client 和 server 的 port 参数）
4. 腾讯云轻量应用服务器有免费额度，适合测试使用
