        // 元素获取
        const inputArea = document.querySelector('.input-area');
        const sendBtn = document.getElementById('sendBtn');
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebarToggle');
        const navItems = document.querySelectorAll('.nav-item');
        const chatHome = document.getElementById('chatHome');
        const featureInterface = document.getElementById('featureInterface');
        const featureTitle = document.getElementById('featureTitle');
        const featureNameDisplay = document.getElementById('featureNameDisplay');
        const newChatBtn = document.getElementById('newChatBtn');
        
        const greetingContainer = document.getElementById('greetingContainer');
        const chatList = document.getElementById('chatList');
        const greetingText = document.getElementById('dynamicGreeting');
        const historyList = document.querySelector('.history-list');
        const hiddenFileInput = document.getElementById('hiddenFileInput');
        const attachBtn = document.getElementById('attachBtn');
        const voiceBtn = document.getElementById('voiceBtn');
        const voiceStatus = document.getElementById('voiceStatus');
        const modePills = document.querySelectorAll('.mode-pill');
        const togglePills = document.querySelectorAll('.toggle-pill');
        let isListening = false;
        let historyCache = [];
        let pendingFile = null; // 待发送的文件
        const featureGreetingMap = {
            guide: [
                '你好，我是操作指导助手，请说明要查询的操作流程。',
                '嗨，需要哪一步操作说明？我可以逐步指导。',
                '你好，想了解哪项操作的步骤？我来帮你梳理。',
                '欢迎，我可以提供操作流程指导，请告诉我场景。'
            ],
            diagnosis: [
                '你好，我是故障诊断助手，请描述故障现象和环境。',
                '嗨，请告诉我设备/系统的异常表现，我来分析。',
                '你好，把报错信息或症状发给我，我帮你诊断。',
                '欢迎，提供故障现象和时间，我协助定位问题。'
            ],
            safety: [
                '你好，我是安全规范助手，请说出你关注的场景或规范。',
                '嗨，需要查询哪类安全要求？我来提供要点。',
                '你好，想了解安全规范的哪些部分？可直接提问。',
                '欢迎，告知业务/场景，我给出相关安全注意事项。'
            ],
            debug: [
                '你好，我是代码调试助手，请粘贴代码片段或错误信息。',
                '嗨，遇到什么编程问题？贴出报错或复现步骤。',
                '你好，描述一下问题和期望结果，我来帮你定位。',
                '欢迎，把报错栈或关键代码发来，我协助排查。'
            ],
            default: [
                '你好，我是助手，请告诉我需要查询的内容。',
                '你好，很高兴为你服务，请说出你的问题。'
            ]
        };
        const commonGreetings = [
            '你好',
            '欢迎回来',
            '很高兴再见到你',
            '准备好开始了吗',
            '今天想聊点什么',
            '需要我帮忙吗',
            '嗨，随时提问'
        ];
        const timeGreetings = {
            morning: ['早上好', '上午好'],
            afternoon: ['下午好', '中午好'],
            evening: ['晚上好', '夜深了，注意休息']
        };

        function currentPeriod() {
            const h = new Date().getHours();
            if (h >= 5 && h < 12) return 'morning';
            if (h >= 12 && h < 18) return 'afternoon';
            return 'evening';
        }

        function setGreeting() {
            if (!greetingText) return;
            const name = 'Lxx';
            const period = currentPeriod();
            const candidates = [
                ...timeGreetings[period].map(t => `${t}，${name}`),
                ...commonGreetings.map(t => `${t}，${name}`)
            ];
            const idx = Math.floor(Math.random() * candidates.length);
            greetingText.textContent = candidates[idx];
        }

        function pickFeatureGreeting(target) {
            const pool = featureGreetingMap[target] || featureGreetingMap.default;
            const idx = Math.floor(Math.random() * pool.length);
            return pool[idx];
        }

        // IDE 界面加载函数
        function loadIDEInterface() {
            const featureInterface = document.getElementById('featureInterface');
            
            // 强制设置容器样式为绝对定位全屏，解决布局依赖和溢出问题
            featureInterface.style.position = 'absolute';
            featureInterface.style.top = '0';
            featureInterface.style.left = '0';
            featureInterface.style.width = '100%';
            featureInterface.style.height = '100%';
            featureInterface.style.zIndex = '10';
            featureInterface.style.overflow = 'hidden';
            featureInterface.style.backgroundColor = '#fff';
            featureInterface.style.display = 'block';
            
            // 设置 IDE 界面的 HTML 内容 - 豆包/Marscode 风格
            featureInterface.innerHTML = `
                <style>
                    .ide-container { display: flex; width: 100%; height: 100%; background: #fff; overflow: hidden; box-sizing: border-box; }
                    .ide-file-panel { width: 220px; flex: 0 1 220px; min-width: 40px; max-width: 40vw; background: #fafafa; border-right: 1px solid #e8e8e8; display: flex; flex-direction: column; overflow: hidden; }
                    .ide-file-panel.collapsed { width: 40px; flex: 0 0 40px; min-width: 40px; }
                    .ide-file-panel.collapsed .ide-file-list, .ide-file-panel.collapsed .ide-file-header span, .ide-file-panel.collapsed .ide-file-header-actions { display: none; }
                    .ide-file-header { padding: 12px 16px; font-size: 13px; font-weight: 500; color: #333; border-bottom: 1px solid #e8e8e8; display: flex; align-items: center; justify-content: space-between; white-space: nowrap; }
                    .ide-file-panel.collapsed .ide-file-header { justify-content: center; padding: 12px 8px; }
                    .ide-toggle-btn { background: none; border: none; cursor: pointer; color: #666; font-size: 16px; padding: 4px; border-radius: 4px; flex-shrink: 0; }
                    .ide-toggle-btn:hover { background: #e8e8e8; color: #333; }
                    .ide-file-header-actions { display: flex; gap: 8px; }
                    .ide-file-header-actions button { background: none; border: none; cursor: pointer; color: #666; font-size: 14px; padding: 2px; }
                    .ide-file-header-actions button:hover { color: #0066ff; }
                    .ide-file-list { flex: 1; overflow-y: auto; padding: 8px 0; }
                    .ide-file-item { display: flex; align-items: center; padding: 6px 16px; cursor: pointer; font-size: 13px; color: #333; gap: 8px; white-space: nowrap; overflow: hidden; }
                    .ide-file-item:hover { background: #f0f0f0; }
                    .ide-file-item.active { background: #e6f0ff; color: #0066ff; }
                    .ide-file-item i { font-size: 14px; color: #f0c040; flex-shrink: 0; }
                    .ide-resize-handle { width: 4px; flex: 0 0 4px; background: transparent; cursor: col-resize; }
                    .ide-resize-handle:hover, .ide-resize-handle.dragging { background: #0066ff; }
                    .ide-resize-handle-h { height: 4px; width: 100%; background: transparent; cursor: row-resize; flex-shrink: 0; }
                    .ide-resize-handle-h:hover, .ide-resize-handle-h.dragging { background: #0066ff; }
                    .ide-editor-panel { flex: 1 1 auto; min-width: 200px; display: flex; flex-direction: column; overflow: hidden; }
                    .ide-editor-panel.collapsed { flex: 0 0 40px; min-width: 40px; }
                    .ide-editor-panel.collapsed .ide-editor-toolbar, .ide-editor-panel.collapsed .ide-editor-main, .ide-editor-panel.collapsed .ide-tab { display: none; }
                    .ide-editor-tabs { display: flex; align-items: center; background: #f5f5f5; border-bottom: 1px solid #e8e8e8; padding: 0 8px; height: 36px; gap: 8px; }
                    .ide-tab { display: flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 13px; color: #666; cursor: pointer; border-bottom: 2px solid transparent; background: transparent; white-space: nowrap; }
                    .ide-tab.active { color: #333; border-bottom-color: #0066ff; background: #fff; }
                    .ide-tab-close { font-size: 12px; color: #999; margin-left: 4px; }
                    .ide-tab-close:hover { color: #ff4d4f; }
                    .ide-editor-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #fff; border-bottom: 1px solid #e8e8e8; flex-wrap: wrap; gap: 8px; }
                    .ide-toolbar-left { display: flex; align-items: center; gap: 12px; }
                    .ide-toolbar-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
                    .ide-lang-select { padding: 4px 8px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; background: #fff; cursor: pointer; }
                    .ide-toolbar-btn { display: flex; align-items: center; gap: 4px; padding: 6px 12px; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
                    .ide-run-btn { background: #0066ff; color: #fff; }
                    .ide-run-btn:hover { background: #0052cc; }
                    .ide-icon-btn { background: transparent; color: #666; padding: 6px; }
                    .ide-icon-btn:hover { background: #f0f0f0; color: #333; }
                    .ide-editor-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-height: 0; }
                    .ide-editor-wrapper { flex: 1; position: relative; min-height: 100px; overflow: hidden; }
                    #ide-editor { width: 100%; height: 100%; }
                    .ide-console-panel { height: 180px; flex: 0 0 180px; border-top: 1px solid #e8e8e8; display: flex; flex-direction: column; background: #f5f5f5; transition: background 0.3s; }
                    .ide-console-panel.collapsed { height: 32px; flex: 0 0 32px; }
                    .ide-console-panel.collapsed .ide-console-output { display: none; }
                    .ide-console-panel.dark { background: #1e1e1e; border-top-color: #404040; }
                    .ide-console-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: #e8e8e8; transition: all 0.3s; cursor: pointer; }
                    .ide-console-panel.dark .ide-console-header { background: #2d2d2d; }
                    .ide-console-title { font-size: 12px; color: #666; display: flex; align-items: center; gap: 6px; transition: all 0.3s; white-space: nowrap; }
                    .ide-console-panel.dark .ide-console-title { color: #ccc; }
                    .ide-console-actions { display: flex; gap: 8px; align-items: center; }
                    .ide-console-actions button { background: none; border: none; color: #666; cursor: pointer; font-size: 12px; padding: 2px 6px; transition: all 0.3s; white-space: nowrap; }
                    .ide-console-actions button:hover { color: #333; }
                    .ide-console-panel.dark .ide-console-actions button { color: #999; }
                    .ide-console-panel.dark .ide-console-actions button:hover { color: #fff; }
                    .ide-console-output { flex: 1; overflow: auto; padding: 8px 12px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; color: #333; line-height: 1.5; transition: all 0.3s; }
                    .ide-console-panel.dark .ide-console-output { color: #d4d4d4; }
                    .ide-ai-panel { width: 380px; flex: 0 1 380px; min-width: 40px; max-width: 45vw; border-left: 1px solid #e8e8e8; display: flex; flex-direction: column; background: #fff; overflow: hidden; }
                    .ide-ai-panel.collapsed { width: 40px; flex: 0 0 40px; min-width: 40px; }
                    .ide-ai-panel.collapsed .ide-ai-messages, .ide-ai-panel.collapsed .ide-ai-input-area, .ide-ai-panel.collapsed .ide-ai-title { display: none; }
                    .ide-ai-header { padding: 12px 16px; border-bottom: 1px solid #e8e8e8; display: flex; align-items: center; justify-content: space-between; }
                    .ide-ai-panel.collapsed .ide-ai-header { justify-content: center; padding: 12px 8px; flex-direction: column; gap: 8px; }
                    .ide-ai-title { font-size: 14px; font-weight: 500; color: #333; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
                    .ide-ai-messages { flex: 1; overflow-y: auto; padding: 16px; min-height: 0; }
                    .ide-ai-message { margin-bottom: 16px; }
                    .ide-ai-message.user { text-align: right; }
                    .ide-ai-message.user .ide-ai-bubble { background: #0066ff; color: #fff; margin-left: auto; }
                    .ide-ai-message.bot .ide-ai-bubble { background: #f5f5f5; color: #333; }
                    .ide-ai-bubble { display: inline-block; max-width: 90%; padding: 10px 14px; border-radius: 12px; font-size: 13px; line-height: 1.5; text-align: left; word-break: break-word; }
                    .ide-ai-input-area { padding: 12px 16px; border-top: 1px solid #e8e8e8; flex-shrink: 0; }
                    .ide-ai-input-wrapper { display: flex; align-items: center; gap: 8px; background: #f5f5f5; border-radius: 8px; padding: 8px 12px; }
                    .ide-ai-input { flex: 1; border: none; background: transparent; font-size: 13px; outline: none; min-width: 0; }
                    .ide-ai-send-btn { background: #0066ff; color: #fff; border: none; border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; flex-shrink: 0; }
                    .ide-ai-send-btn:hover { background: #0052cc; }
                </style>
                <div class="ide-container">
                    <!-- 左侧文件面板 -->
                    <div class="ide-file-panel" id="ide-file-panel">
                        <div class="ide-file-header">
                            <button class="ide-toggle-btn" id="ide-toggle-files" title="收起/展开"><i class="ri-layout-left-line"></i></button>
                            <span>文件</span>
                            <div class="ide-file-header-actions">
                                <button id="ide-new-file-btn" title="新建文件"><i class="ri-file-add-line"></i></button>
                                <button id="ide-refresh-btn" title="刷新"><i class="ri-refresh-line"></i></button>
                            </div>
                        </div>
                        <div class="ide-file-list" id="ide-file-list">
                            <div class="ide-file-item active">
                                <i class="ri-file-code-line"></i>
                                <span>main.py</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 左侧拖拽条 -->
                    <div class="ide-resize-handle" id="ide-resize-left"></div>

                    <!-- 中间编辑器面板 -->
                    <div class="ide-editor-panel" id="ide-editor-panel">
                        <div class="ide-editor-tabs">
                            <button class="ide-toggle-btn" id="ide-toggle-editor" title="收起/展开编辑器"><i class="ri-code-s-slash-line"></i></button>
                            <div class="ide-tab active">
                                <i class="ri-file-code-line" style="color: #f0c040; font-size: 14px;"></i>
                                <span>main.py</span>
                                <span class="ide-tab-close">×</span>
                            </div>
                        </div>
                        <div class="ide-editor-toolbar">
                            <div class="ide-toolbar-left">
                                <select id="ide-language-select" class="ide-lang-select">
                                    <option value="python" selected>Python</option>
                                    <option value="javascript">JavaScript</option>
                                    <option value="java">Java</option>
                                    <option value="c">C</option>
                                    <option value="cpp">C++</option>
                                    <option value="go">Go</option>
                                    <option value="rust">Rust</option>
                                    <option value="typescript">TypeScript</option>
                                </select>
                            </div>
                            <div class="ide-toolbar-right">
                                <button id="ide-format-btn" class="ide-toolbar-btn ide-icon-btn" title="格式化"><i class="ri-magic-line"></i></button>
                                <button id="ide-save-btn" class="ide-toolbar-btn ide-icon-btn" title="保存"><i class="ri-save-line"></i></button>
                                <button id="ide-theme-btn" class="ide-toolbar-btn ide-icon-btn" title="切换主题"><i class="ri-moon-line"></i></button>
                                <button id="ide-run-btn" class="ide-toolbar-btn ide-run-btn"><i class="ri-play-fill"></i> 运行</button>
                            </div>
                        </div>
                        <div class="ide-editor-main">
                            <div class="ide-editor-wrapper">
                                <div id="ide-editor"></div>
                            </div>
                            <!-- 控制台拖拽条 -->
                            <div class="ide-resize-handle-h" id="ide-resize-console"></div>
                            <div class="ide-console-panel" id="ide-console-panel">
                                <div class="ide-console-header" id="ide-console-header">
                                    <span class="ide-console-title"><i class="ri-terminal-box-line"></i> 控制台</span>
                                    <div class="ide-console-actions">
                                        <button id="ide-toggle-console" title="收起/展开"><i class="ri-arrow-down-s-line"></i></button>
                                        <button id="ide-clear-console-btn">清空</button>
                                        <button id="ide-copy-output-btn">复制</button>
                                    </div>
                                </div>
                                <div class="ide-console-output" id="ide-console-output">
                                    <div style="color: #999;">// 准备就绪，点击运行按钮执行代码</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 右侧拖拽条 -->
                    <div class="ide-resize-handle" id="ide-resize-right"></div>

                    <!-- 右侧AI对话面板 -->
                    <div class="ide-ai-panel" id="ide-ai-panel">
                        <div class="ide-ai-header">
                            <span class="ide-ai-title"><i class="ri-robot-line"></i> AI 助手</span>
                            <div style="display: flex; gap: 4px;">
                                <button class="ide-toolbar-btn ide-icon-btn" id="ide-ai-clear-btn" title="清空对话"><i class="ri-delete-bin-line"></i></button>
                                <button class="ide-toggle-btn" id="ide-toggle-ai" title="收起/展开"><i class="ri-layout-right-line"></i></button>
                            </div>
                        </div>
                        <div class="ide-ai-messages" id="ide-ai-messages">
                            <div class="ide-ai-message bot">
                                <div class="ide-ai-bubble">你好！我是代码调试助手，可以帮你：<br>• 解释代码逻辑<br>• 分析错误原因<br>• 优化代码性能<br>• 回答编程问题<br><br>有什么可以帮你的？</div>
                            </div>
                        </div>
                        <div class="ide-ai-input-area">
                            <div class="ide-ai-input-wrapper">
                                <input type="text" class="ide-ai-input" id="ide-ai-input" placeholder="输入问题或粘贴代码...">
                                <button class="ide-ai-send-btn" id="ide-ai-send-btn"><i class="ri-send-plane-fill"></i></button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 初始化 Monaco Editor
            initIDEMonaco();
        }

        // 初始化 IDE 的 Monaco Editor
        let ideEditor = null;
        let ideCurrentTheme = 'vs-light';  // 默认浅色主题，编辑器和控制台都是白色
        let ideCurrentLanguage = 'python';
        let ideSessionId = null;

        function initIDEMonaco() {
            // 加载 Monaco Editor
            const script = document.createElement('script');
            script.src = 'https://cdn.bootcdn.net/ajax/libs/monaco-editor/0.44.0/min/vs/loader.js';
            script.onload = () => {
                require.config({
                    paths: { 'vs': 'https://cdn.bootcdn.net/ajax/libs/monaco-editor/0.44.0/min/vs' }
                });

                require(['vs/editor/editor.main'], function() {
                    ideEditor = monaco.editor.create(document.getElementById('ide-editor'), {
                        value: getIDEDefaultCode('python'),
                        language: 'python',
                        theme: ideCurrentTheme,
                        lineNumbers: 'on',
                        automaticLayout: true
                    });
                    
                    // 同步控制台主题与编辑器
                    const consolePanel = document.querySelector('.ide-console-panel');
                    if (ideCurrentTheme === 'vs-light') {
                        consolePanel.classList.add('light');
                    } else {
                        consolePanel.classList.remove('light');
                    }
                    
                    // 设置事件监听
                    setupIDEEventListeners();
                    
                    // 初始化会话
                    initIDESession();
                });
            };
            document.head.appendChild(script);
        }

        function getIDEDefaultCode(language) {
            const defaultCodes = {
                python: `# Python 示例代码\nprint("Hello, Python Web IDE!")\n\nfor i in range(5):\n    print(f"循环次数: {i}")`,
                javascript: `// JavaScript 示例\nconsole.log("Hello, Web IDE!");\n\nfor (let i = 0; i < 5; i++) {\n    console.log(\`循环次数: \${i}\`);\n}`,
                java: `// Java 示例\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, Web IDE!");\n        \n        for (int i = 0; i < 5; i++) {\n            System.out.println("循环次数: " + i);\n        }\n    }\n}`,
                c: `// C 示例\n#include <stdio.h>\n\nint main() {\n    printf("Hello, Web IDE!\\n");\n    \n    for (int i = 0; i < 5; i++) {\n        printf("循环次数: %d\\n", i);\n    }\n    \n    return 0;\n}`,
                cpp: `// C++ 示例\n#include <iostream>\n\nint main() {\n    std::cout << "Hello, Web IDE!" << std::endl;\n    \n    for (int i = 0; i < 5; i++) {\n        std::cout << "循环次数: " << i << std::endl;\n    }\n    \n    return 0;\n}`,
                go: `// Go 示例\npackage main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, Web IDE!")\n    \n    for i := 0; i < 5; i++ {\n        fmt.Printf("循环次数: %d\\n", i)\n    }\n}`,
                rust: `// Rust 示例\nfn main() {\n    println!("Hello, Web IDE!");\n    \n    for i in 0..5 {\n        println!("循环次数: {}", i);\n    }\n}`,
                typescript: `// TypeScript 示例\nconsole.log("Hello, Web IDE!");\n\nfor (let i: number = 0; i < 5; i++) {\n    console.log(\`循环次数: \${i}\`);\n}`
            };
            return defaultCodes[language] || '';
        }

        async function initIDESession() {
            try {
                const response = await fetch('/api/ide/session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                ideSessionId = data.session_id;
                console.log('IDE 会话已创建:', ideSessionId);
            } catch (error) {
                console.error('创建 IDE 会话失败:', error);
                appendIDEOutput('⚠️ 创建会话失败，某些功能可能不可用', 'error');
            }
        }

        function setupIDEEventListeners() {
            // 运行按钮
            document.getElementById('ide-run-btn').addEventListener('click', runIDECode);
            
            // 保存按钮
            document.getElementById('ide-save-btn').addEventListener('click', () => {
                appendIDEOutput('💾 代码已保存', 'success');
            });
            
            // 语言切换
            document.getElementById('ide-language-select').addEventListener('change', (e) => {
                ideCurrentLanguage = e.target.value;
                monaco.editor.setModelLanguage(ideEditor.getModel(), ideCurrentLanguage);
                ideEditor.setValue(getIDEDefaultCode(ideCurrentLanguage));
                // 更新文件名显示
                const langExtensions = { python: 'py', javascript: 'js', java: 'java', c: 'c', cpp: 'cpp', go: 'go', rust: 'rs', typescript: 'ts' };
                const ext = langExtensions[ideCurrentLanguage] || 'txt';
                document.querySelector('.ide-tab span').textContent = `main.${ext}`;
                document.querySelector('.ide-file-item span').textContent = `main.${ext}`;
            });
            
            // 主题切换
            document.getElementById('ide-theme-btn').addEventListener('click', () => {
                ideCurrentTheme = ideCurrentTheme === 'vs-dark' ? 'vs-light' : 'vs-dark';
                monaco.editor.setTheme(ideCurrentTheme);
                const themeBtn = document.getElementById('ide-theme-btn');
                themeBtn.innerHTML = ideCurrentTheme === 'vs-dark' ? '<i class="ri-sun-line"></i>' : '<i class="ri-moon-line"></i>';
                
                // 同步控制台主题
                const consolePanel = document.querySelector('.ide-console-panel');
                if (ideCurrentTheme === 'vs-dark') {
                    consolePanel.classList.add('dark');
                } else {
                    consolePanel.classList.remove('dark');
                }
            });
            
            // 清空控制台
            document.getElementById('ide-clear-console-btn').addEventListener('click', clearIDEConsole);
            
            // 复制输出
            document.getElementById('ide-copy-output-btn').addEventListener('click', copyIDEOutput);
            
            // 新建文件按钮
            document.getElementById('ide-new-file-btn').addEventListener('click', () => {
                const filename = prompt('请输入文件名:', 'untitled.py');
                if (filename) {
                    appendIDEOutput(`📄 新建文件: ${filename}`, 'info');
                }
            });
            
            // AI 对话发送
            document.getElementById('ide-ai-send-btn').addEventListener('click', sendIDEAIMessage);
            document.getElementById('ide-ai-input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendIDEAIMessage();
            });
            
            // AI 清空对话
            document.getElementById('ide-ai-clear-btn').addEventListener('click', () => {
                document.getElementById('ide-ai-messages').innerHTML = `
                    <div class="ide-ai-message bot">
                        <div class="ide-ai-bubble">对话已清空，有什么可以帮你的？</div>
                    </div>
                `;
            });
            
            // ========== 面板收起/展开功能 ==========
            
            // 左侧文件面板收起/展开
            document.getElementById('ide-toggle-files').addEventListener('click', () => {
                const panel = document.getElementById('ide-file-panel');
                panel.classList.toggle('collapsed');
                if (ideEditor) ideEditor.layout();
            });
            
            // 中间编辑器面板收起/展开
            document.getElementById('ide-toggle-editor').addEventListener('click', () => {
                const panel = document.getElementById('ide-editor-panel');
                panel.classList.toggle('collapsed');
                if (ideEditor) ideEditor.layout();
            });
            
            // 右侧AI面板收起/展开
            document.getElementById('ide-toggle-ai').addEventListener('click', () => {
                const panel = document.getElementById('ide-ai-panel');
                panel.classList.toggle('collapsed');
                if (ideEditor) ideEditor.layout();
            });
            
            // 控制台收起/展开
            document.getElementById('ide-toggle-console').addEventListener('click', () => {
                const panel = document.getElementById('ide-console-panel');
                panel.classList.toggle('collapsed');
                const icon = document.querySelector('#ide-toggle-console i');
                icon.className = panel.classList.contains('collapsed') ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line';
                if (ideEditor) ideEditor.layout();
            });
            
            // ========== 拖拽调整大小功能 ==========
            
            // 左侧拖拽条 - 调整文件面板宽度
            setupResizeHandle('ide-resize-left', 'ide-file-panel', 100, 400, false);
            
            // 右侧拖拽条 - 调整AI面板宽度
            setupResizeHandle('ide-resize-right', 'ide-ai-panel', 200, 600, true);
            
            // 控制台拖拽条
            setupResizeHandleVertical('ide-resize-console', 'ide-console-panel', 50, 400);
        }
        
        // 水平拖拽调整大小
        function setupResizeHandle(handleId, panelId, min, max, reverse) {
            const handle = document.getElementById(handleId);
            const panel = document.getElementById(panelId);
            if (!handle || !panel) return;
            
            let startX, startWidth, maxAllowedWidth;
            
            handle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                startX = e.clientX;
                startWidth = panel.offsetWidth;
                handle.classList.add('dragging');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                
                // 计算允许的最大宽度，防止溢出
                const container = panel.parentElement;
                let otherWidth = 0;
                Array.from(container.children).forEach(child => {
                    if (child === panel) return;
                    if (getComputedStyle(child).display === 'none') return;
                    if (getComputedStyle(child).position === 'absolute') return;
                    
                    if (child.classList.contains('ide-editor-panel')) {
                        otherWidth += parseFloat(getComputedStyle(child).minWidth) || 200;
                    } else {
                        otherWidth += child.offsetWidth;
                    }
                });
                // 预留一点缓冲空间(例如2px)，防止计算误差导致的微小溢出
                maxAllowedWidth = container.clientWidth - otherWidth - 2;
                
                const onMouseMove = (e) => {
                    let diff;
                    if (reverse) {
                        diff = startX - e.clientX;
                    } else {
                        diff = e.clientX - startX;
                    }
                    
                    const effectiveMax = Math.min(max, Math.max(min, maxAllowedWidth));
                    const newWidth = Math.min(effectiveMax, Math.max(min, startWidth + diff));
                    
                    panel.style.width = newWidth + 'px';
                    // Allow panel to shrink if needed to avoid overflow
                    panel.style.flex = '0 1 ' + newWidth + 'px';
                    if (ideEditor) ideEditor.layout();
                };
                
                const onMouseUp = () => {
                    handle.classList.remove('dragging');
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    if (ideEditor) ideEditor.layout();
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }
        
        // 垂直拖拽调整大小
        function setupResizeHandleVertical(handleId, panelId, min, max) {
            const handle = document.getElementById(handleId);
            const panel = document.getElementById(panelId);
            if (!handle || !panel) return;
            
            let startY, startHeight;
            
            handle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                startY = e.clientY;
                startHeight = panel.offsetHeight;
                handle.classList.add('dragging');
                document.body.style.cursor = 'row-resize';
                document.body.style.userSelect = 'none';
                
                const onMouseMove = (e) => {
                    const diff = startY - e.clientY;
                    const newHeight = Math.min(max, Math.max(min, startHeight + diff));
                    panel.style.height = newHeight + 'px';
                    panel.style.flex = '0 0 ' + newHeight + 'px';
                    if (ideEditor) ideEditor.layout();
                };
                
                const onMouseUp = () => {
                    handle.classList.remove('dragging');
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    if (ideEditor) ideEditor.layout();
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }
        
        // AI 对话发送函数
        async function sendIDEAIMessage() {
            const input = document.getElementById('ide-ai-input');
            const message = input.value.trim();
            if (!message) return;
            
            const messagesContainer = document.getElementById('ide-ai-messages');
            
            // 添加用户消息
            messagesContainer.innerHTML += `
                <div class="ide-ai-message user">
                    <div class="ide-ai-bubble">${message}</div>
                </div>
            `;
            input.value = '';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // 获取当前代码
            const currentCode = ideEditor ? ideEditor.getValue() : '';
            const language = ideCurrentLanguage || 'python';
            
            // 添加加载提示
            const loadingId = 'loading-' + Date.now();
            messagesContainer.innerHTML += `
                <div class="ide-ai-message bot" id="${loadingId}">
                    <div class="ide-ai-bubble">正在分析代码...</div>
                </div>
            `;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            try {
                // 调用代码调试接口
                // 使用 null 让后端自动使用 .env 配置，避免 provider ID 不匹配问题
                const response = await fetch('/api/ide/debug', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: currentCode,
                        language: language,
                        user_question: message,
                        session_id: ideSessionId,
                        model: null,
                        provider_id: null,
                        api_key: null,
                        base_url: null
                    })
                });
                
                // 移除加载提示
                document.getElementById(loadingId)?.remove();
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `HTTP ${response.status}`);
                }
                
                // 流式读取响应
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let aiResponse = '';
                
                // 创建 AI 回复容器
                const aiMessageId = 'ai-' + Date.now();
                messagesContainer.innerHTML += `
                    <div class="ide-ai-message bot" id="${aiMessageId}">
                        <div class="ide-ai-bubble"></div>
                    </div>
                `;
                
                const aiMessageBubble = document.querySelector(`#${aiMessageId} .ide-ai-bubble`);
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    aiResponse += chunk;
                    
                    // 使用 marked 渲染 Markdown
                    if (typeof marked !== 'undefined') {
                        aiMessageBubble.innerHTML = marked.parse(aiResponse);
                    } else {
                        aiMessageBubble.innerHTML = aiResponse.replace(/\n/g, '<br>');
                    }
                    
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
                
            } catch (error) {
                // 移除加载提示
                document.getElementById(loadingId)?.remove();
                
                // 显示错误
                messagesContainer.innerHTML += `
                    <div class="ide-ai-message bot">
                        <div class="ide-ai-bubble" style="color: #ff6b6b;">
                            ❌ 调试失败: ${error.message}<br><br>
                            <strong>可能的原因：</strong><br>
                            • API 配置未设置（请在设置中配置 API）<br>
                            • 网络连接问题<br>
                            • 模型服务不可用<br><br>
                            <strong>解决方法：</strong><br>
                            1. 点击侧边栏的"设置"按钮<br>
                            2. 切换到"API 管理"标签<br>
                            3. 配置你的 API Key 和 Base URL<br>
                            4. 返回 IDE 重试
                        </div>
                    </div>
                `;
            }
            
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        async function runIDECode() {
            const code = ideEditor.getValue();
            const language = ideCurrentLanguage;
            
            clearIDEConsole();
            appendIDEOutput('⏳ 正在运行代码...', 'info');
            
            try {
                const response = await fetch('/api/ide/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code, language, session_id: ideSessionId })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    appendIDEOutput(`✅ 运行成功 (${result.language} ${result.version})`, 'success');
                    if (result.compile_output) {
                        appendIDEOutput(`\n编译输出:\n${result.compile_output}`, 'info');
                    }
                    if (result.output) {
                        appendIDEOutput(`\n输出:\n${result.output}`, 'success');
                    }
                    appendIDEOutput(`\n⏱️ 执行时间: ${result.run_time}s`, 'info');
                } else {
                    appendIDEOutput('❌ 运行失败', 'error');
                    if (result.error) {
                        appendIDEOutput(`\n错误:\n${result.error}`, 'error');
                    }
                }
            } catch (error) {
                appendIDEOutput(`❌ 网络错误: ${error.message}`, 'error');
            }
        }

        function appendIDEOutput(text, type = 'info') {
            const consoleOutput = document.getElementById('ide-console-output');
            const line = document.createElement('div');
            const isDark = document.querySelector('.ide-console-panel')?.classList.contains('dark');
            
            // 根据主题选择颜色
            const darkColors = {
                'info': '#74c0fc',
                'success': '#51cf66',
                'error': '#ff6b6b'
            };
            const lightColors = {
                'info': '#0066ff',
                'success': '#00a854',
                'error': '#f5222d'
            };
            const colors = isDark ? darkColors : lightColors;
            
            line.style.color = colors[type] || (isDark ? '#d4d4d4' : '#333');
            line.style.margin = '2px 0';
            line.textContent = text;
            consoleOutput.appendChild(line);
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }

        function clearIDEConsole() {
            const isDark = document.querySelector('.ide-console-panel')?.classList.contains('dark');
            document.getElementById('ide-console-output').innerHTML = `<div style="color: ${isDark ? '#6a9955' : '#999'};">// 准备就绪，点击运行按钮执行代码</div>`;
        }

        function copyIDEOutput() {
            const text = document.getElementById('ide-console-output').innerText;
            navigator.clipboard.writeText(text).then(() => {
                appendIDEOutput('✅ 已复制到剪贴板', 'success');
            });
        }

        // Settings Modal Elements
        const settingsBtn = document.getElementById('settingsBtn');
        const settingsModal = document.getElementById('settingsModal');
        const closeSettingsBtn = document.getElementById('closeSettingsBtn');
        // const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        // const apiBaseUrlInput = document.getElementById('apiBaseUrl');
        // const apiKeyInput = document.getElementById('apiKey');

        // Model Config Modal Elements
        const modelConfigBtn = document.getElementById('modelConfigBtn');
        const modelConfigModal = document.getElementById('modelConfigModal');
        const closeModelConfigBtn = document.getElementById('closeModelConfigBtn');
        const saveModelConfigBtn = document.getElementById('saveModelConfigBtn');
        const llmSelect = document.getElementById('llmSelect');
        const ocrSelect = document.getElementById('ocrSelect');
        const asrSelect = document.getElementById('asrSelect');
        const ttsSelect = document.getElementById('ttsSelect');
        const systemPromptInput = document.getElementById('systemPrompt');

        // Provider Config Modal Elements
        const providerConfigModal = document.getElementById('providerConfigModal');
        const closeProviderConfigBtn = document.getElementById('closeProviderConfigBtn');
        const saveProviderConfigBtn = document.getElementById('saveProviderConfigBtn');
        const providerConfigTitle = document.getElementById('providerConfigTitle');
        const providerApiKeyInput = document.getElementById('providerApiKey');
        const providerBaseUrlInput = document.getElementById('providerBaseUrl');
        
        let currentProviderId = null;

        window.addEventListener('DOMContentLoaded', () => {
            // 初始化 marked 配置（全局只需配置一次）
            marked.use(markedHighlight.markedHighlight({
                langPrefix: 'hljs language-',
                highlight(code, lang) {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                }
            }));
            
            loadHistory();
            setGreeting();
            // 恢复模式高亮
            initMode();
            // 恢复开关状态
            initToggles();
            // 预加载模型列表
            loadModels();
            
            // Add click listeners to provider cards
            const providerCards = document.querySelectorAll('.provider-card');
            providerCards.forEach(card => {
                card.addEventListener('click', () => {
                    const providerId = card.getAttribute('data-provider-id');
                    const providerName = card.getAttribute('data-provider-name');
                    
                    openProviderConfig(providerId, providerName);
                });
            });
        });

        // 极速/思考模式切换
        function initMode() {
            const savedMode = localStorage.getItem('chatMode') || 'fast';
            setMode(savedMode);
            modePills.forEach(pill => {
                pill.addEventListener('click', () => {
                    const mode = pill.dataset.mode;
                    setMode(mode);
                });
            });
        }

        function setMode(mode) {
            modePills.forEach(pill => {
                pill.classList.toggle('active', pill.dataset.mode === mode);
            });
            localStorage.setItem('chatMode', mode);
        }

        // 通用开关（如“联网”）
        function initToggles() {
            togglePills.forEach(pill => {
                const key = `toggle_${pill.dataset.toggle}`;
                const saved = localStorage.getItem(key);
                const isOn = saved === null ? false : saved === 'true';
                setToggle(pill, isOn, key);
                pill.addEventListener('click', () => {
                    const current = pill.classList.contains('active');
                    setToggle(pill, !current, key);
                });
            });
        }

        function setToggle(pill, on, key) {
            pill.classList.toggle('active', on);
            localStorage.setItem(key, on);
        }

        async function loadModels() {
            try {
                const res = await fetch('/api/llm_config');
                const data = await res.json();
                const providers = data.providers || [];
                
                // 同时加载系统提示词配置
                try {
                    const promptRes = await fetch('/api/system_prompt');
                    const promptData = await promptRes.json();
                    systemPromptInput.value = promptData.default || '';
                } catch (e) {
                    console.warn('加载系统提示词失败', e);
                }
                
                // 清空
                llmSelect.innerHTML = '';
                ocrSelect.innerHTML = '';
                asrSelect.innerHTML = '';
                ttsSelect.innerHTML = '';

                // 为 llmSelect 创建分组
                const llmGroup = document.createElement('optgroup'); llmGroup.label = '文本大模型';
                const vlGroup = document.createElement('optgroup'); vlGroup.label = '多模态大模型';
                llmSelect.appendChild(llmGroup);
                llmSelect.appendChild(vlGroup);

                // 辅助函数
                const createOption = (p, m) => {
                    const opt = document.createElement('option');
                    opt.value = JSON.stringify({ provider: p.id, model: m.id });
                    opt.textContent = `${p.name} / ${m.id}`;
                    return opt;
                };

                providers.forEach(p => {
                    const type = p.type || 'llm';
                    (p.models || []).forEach(m => {
                        const opt = createOption(p, m);
                        if (type === 'llm') {
                            llmGroup.appendChild(opt);
                        } else if (type === 'vl') {
                            vlGroup.appendChild(opt);
                        } else if (type === 'ocr') {
                            ocrSelect.appendChild(opt);
                        } else if (type === 'asr') {
                            asrSelect.appendChild(opt);
                        } else if (type === 'tts') {
                            ttsSelect.appendChild(opt);
                        } else {
                            llmGroup.appendChild(opt);
                        }
                    });
                });
                
                // 如果分组为空，清理一下
                if (llmGroup.children.length === 0) llmGroup.remove();
                if (vlGroup.children.length === 0) vlGroup.remove();

                // 恢复选择
                const restore = (select, key) => {
                    const saved = localStorage.getItem(key);
                    if (saved) {
                        // 尝试匹配 value
                        for (let opt of select.options) {
                             // 简单包含匹配，因为 saved 可能只是 model id 或者 json 格式不同
                            if (opt.value === saved || opt.value.indexOf(saved) !== -1) {
                                select.value = opt.value;
                                break;
                            }
                        }
                    }
                };

                restore(llmSelect, 'selectedModel');
                restore(ocrSelect, 'selectedOcrModel');
                restore(asrSelect, 'selectedAsrModel');
                restore(ttsSelect, 'selectedTtsModel');

            } catch (err) {
                console.error('加载模型配置失败', err);
            }
        }

        // 会话管理
        let currentSessionId = ''; // 如果为空，表示新对话，发送第一条消息时会生成或复用
        let currentChatType = ''; // 当前问答类型: guide/diagnosis/safety/debug，空表示普通对话

        // 生成 UUID
        function generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        async function loadHistory() {
            try {
                // 不传 session_id 获取会话列表
                const res = await fetch('/api/history?limit=50');
                if (!res.ok) {
                    throw new Error(`服务器响应错误: ${res.status}`);
                }
                const data = await res.json();
                historyCache = data.history || [];
                renderHistory(historyCache);
            } catch (e) {
                console.error('加载历史失败', e);
                // 如果加载失败，保留原有的静态列表（虽然不可点击，但总比空白好）
                // 或者显示一个错误提示
            }
        }

        // ...

        function renderHistory(sessions) {
            if (!historyList) return;
            historyList.innerHTML = '';
            
            sessions.forEach(session => {
                const title = session.title || '新对话';
                const time = session.timestamp ? session.timestamp.replace('T',' ').split('.')[0] : '';
                const li = document.createElement('li');
                li.className = 'history-item';
                // 高亮当前会话
                if (session.session_id === currentSessionId) {
                    li.classList.add('active');
                }
                
                li.innerHTML = `
                    <i class="ri-message-3-line"></i>
                    <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${title}">${title}</div>
                    <button class="delete-session-btn" data-sid="${session.session_id}" title="删除" style="background:none;border:none;cursor:pointer;color:#999;padding:2px;display:none;">
                        <i class="ri-delete-bin-line"></i>
                    </button>
                `;
                // 点击切换会话
                li.addEventListener('click', (e) => {
                    if (e.target.closest('.delete-session-btn')) return;
                    switchSession(session.session_id);
                });
                // 悬停显示删除按钮
                li.addEventListener('mouseenter', () => {
                    const btn = li.querySelector('.delete-session-btn');
                    if (btn) btn.style.display = 'block';
                });
                li.addEventListener('mouseleave', () => {
                    const btn = li.querySelector('.delete-session-btn');
                    if (btn) btn.style.display = 'none';
                });
                // 删除按钮点击
                const deleteBtn = li.querySelector('.delete-session-btn');
                if (deleteBtn) {
                    deleteBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        const sid = deleteBtn.dataset.sid;
                        if (!confirm('确定删除这个对话吗？')) return;
                        try {
                            await fetch(`/api/session/${sid}`, { method: 'DELETE' });
                            // 如果删除的是当前会话，重置
                            if (sid === currentSessionId) {
                                currentSessionId = '';
                                greetingContainer.style.display = 'block';
                                chatList.style.display = 'none';
                                chatList.innerHTML = '';
                            }
                            loadHistory();
                        } catch (err) {
                            console.error('删除失败', err);
                        }
                    });
                }
                historyList.appendChild(li);
            });
        }

        async function switchSession(sid) {
            if (!sid) return;
            currentSessionId = sid;
            
            // 确保显示聊天界面，隐藏功能界面
            featureInterface.style.display = 'none';
            chatHome.style.display = 'flex';
            // 取消所有导航高亮
            navItems.forEach(i => i.classList.remove('active'));

            // 重新渲染历史列表以更新高亮
            renderHistory(historyCache);

            try {
                const res = await fetch(`/api/history?session_id=${sid}`);
                const data = await res.json();
                const messages = data.history || [];
                renderConversation(messages);
            } catch (e) {
                console.error('加载会话详情失败', e);
            }
        }

        function renderConversation(items) {
            if (!items) return;
            greetingContainer.style.display = 'none';
            chatList.style.display = 'flex';
            chatList.innerHTML = ''; // 清空当前视图
            
            items.forEach(item => {
                // 根据 role 决定 sender
                const sender = (item.role === 'user') ? 'user' : 'bot';
                // 从 meta 中获取知识库来源
                const kbSources = (item.meta && item.meta.kb_sources) ? item.meta.kb_sources : null;
                // 从 meta 中获取文件信息
                const fileInfo = (item.meta && item.meta.file_url) ? {
                    url: item.meta.file_url,
                    filename: item.meta.filename || ''
                } : null;
                
                // 从 meta 中获取模型信息
                const modelInfo = (sender === 'bot') ? {
                    model: (item.meta && item.meta.model) ? item.meta.model : null,
                    timestamp: item.timestamp
                } : null;
                
                appendMessage(item.content, sender, false, kbSources, fileInfo, modelInfo);
            });
            // 滚动到底部
            chatList.scrollTop = chatList.scrollHeight;
        }

        function openProviderConfig(providerId, providerName) {
            currentProviderId = providerId;
            providerConfigTitle.textContent = `${providerName} 配置`;
            
            // Load saved config for this provider
            const savedKey = localStorage.getItem(`provider_key_${providerId}`);
            const savedUrl = localStorage.getItem(`provider_url_${providerId}`);
            
            providerApiKeyInput.value = savedKey || '';
            providerBaseUrlInput.value = savedUrl || '';
            
            // Temporarily hide the main settings modal (optional, or keep it open behind)
            // settingsModal.style.display = 'none'; 
            
            // Show provider config modal
            providerConfigModal.style.display = 'flex';
        }

        closeProviderConfigBtn.addEventListener('click', () => {
            providerConfigModal.style.display = 'none';
            // settingsModal.style.display = 'flex'; // Re-show main modal if we hid it
        });

        saveProviderConfigBtn.addEventListener('click', () => {
            if (!currentProviderId) return;
            
            const apiKey = providerApiKeyInput.value;
            const baseUrl = providerBaseUrlInput.value;
            
            localStorage.setItem(`provider_key_${currentProviderId}`, apiKey);
            localStorage.setItem(`provider_url_${currentProviderId}`, baseUrl);
            
            providerConfigModal.style.display = 'none';
            // settingsModal.style.display = 'flex';
            
            alert('配置已保存');
        });

        // Settings Modal Logic
        settingsBtn.addEventListener('click', () => {
            settingsModal.style.display = 'flex';
            loadApiStatus(); // 加载 API 状态
            loadScenarioPrompts(); // 加载场景提示词预览
        });

        closeSettingsBtn.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });

        // 设置标签页切换
        document.querySelectorAll('.settings-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // 移除所有 active 类
                document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.settings-tab-content').forEach(c => c.classList.remove('active'));
                
                // 添加 active 类到当前标签
                tab.classList.add('active');
                const tabName = tab.dataset.tab;
                document.getElementById(tabName + 'Tab').classList.add('active');
            });
        });

        // API 配置相关
        const apiConfigModal = document.getElementById('apiConfigModal');
        const closeApiConfigBtn = document.getElementById('closeApiConfigBtn');
        const cancelApiConfigBtn = document.getElementById('cancelApiConfigBtn');
        const saveApiConfigBtn = document.getElementById('saveApiConfigBtn');
        const apiKeyInput = document.getElementById('apiKeyInput');
        const apiBaseUrlInput = document.getElementById('apiBaseUrlInput');
        const apiConfigTitle = document.getElementById('apiConfigTitle');
        let currentApiProvider = '';

        // 加载 API 状态（从 .env 和 localStorage 合并）
        async function loadApiStatus() {
            const providers = ['qwen', 'openai', 'volcengine', 'deepseek', 'local'];
            
            try {
                // 从后端获取 .env 配置
                const response = await fetch('/api/env/config');
                const data = await response.json();
                
                if (data.success && data.config) {
                    providers.forEach(provider => {
                        // localStorage 优先，如果没有则使用 .env 的配置
                        const localKey = localStorage.getItem(`${provider}_api_key`);
                        const envConfig = data.config[provider];
                        const hasConfig = localKey || (envConfig && envConfig.has_config);
                        
                        const statusEl = document.querySelector(`.api-provider-status[data-provider="${provider}"]`);
                        if (statusEl) {
                            if (hasConfig) {
                                statusEl.textContent = '已配置';
                                statusEl.classList.add('configured');
                            } else {
                                statusEl.textContent = '未配置';
                                statusEl.classList.remove('configured');
                            }
                        }
                    });
                }
            } catch (e) {
                console.error('加载 API 配置失败:', e);
                // 降级到只使用 localStorage
                providers.forEach(provider => {
                    const apiKey = localStorage.getItem(`${provider}_api_key`);
                    const statusEl = document.querySelector(`.api-provider-status[data-provider="${provider}"]`);
                    if (statusEl) {
                        if (apiKey) {
                            statusEl.textContent = '已配置';
                            statusEl.classList.add('configured');
                        } else {
                            statusEl.textContent = '未配置';
                            statusEl.classList.remove('configured');
                        }
                    }
                });
            }
        }

        // 加载场景提示词预览（显示前50个字符）
        async function loadScenarioPrompts() {
            const scenarios = ['operation_guide', 'fault_diagnosis', 'safety_regulation', 'code_debug'];
            
            for (const scenario of scenarios) {
                try {
                    const response = await fetch(`/api/scenario/prompt?scenario=${scenario}`);
                    const data = await response.json();
                    
                    if (data.success && data.prompt) {
                        // 更新场景描述，显示提示词的前50个字符
                        const promptItem = document.querySelector(`.prompt-edit-btn[data-scenario="${scenario}"]`)?.closest('.prompt-item');
                        if (promptItem) {
                            const descEl = promptItem.querySelector('.prompt-desc');
                            if (descEl) {
                                const preview = data.prompt.substring(0, 50).replace(/\n/g, ' ') + '...';
                                descEl.setAttribute('title', data.prompt); // 完整内容作为 tooltip
                            }
                        }
                    }
                } catch (e) {
                    console.error(`加载场景 ${scenario} 提示词失败:`, e);
                }
            }
        }

        // API 配置按钮点击（从 .env 和 localStorage 加载）
        document.querySelectorAll('.api-config-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                currentApiProvider = btn.dataset.provider;
                const providerNames = {
                    'qwen': '通义千问',
                    'openai': 'ChatGPT',
                    'volcengine': '火山引擎',
                    'deepseek': '深度求索',
                    'local': '本地模型'
                };
                
                apiConfigTitle.textContent = `配置 ${providerNames[currentApiProvider]}`;
                
                // 先从 localStorage 加载
                let savedKey = localStorage.getItem(`${currentApiProvider}_api_key`) || '';
                let savedBaseUrl = localStorage.getItem(`${currentApiProvider}_base_url`) || '';
                
                // 如果 localStorage 没有，尝试从 .env 加载
                if (!savedKey || !savedBaseUrl) {
                    try {
                        const response = await fetch('/api/env/config');
                        const data = await response.json();
                        
                        if (data.success && data.config && data.config[currentApiProvider]) {
                            const envConfig = data.config[currentApiProvider];
                            // 后端出于安全考虑不再返回 API Key 明文；
                            // 已在 .env 配置的密钥由后端自动使用，前端无需填写
                            if (!savedKey && envConfig.has_config) {
                                apiKeyInput.placeholder = '已在服务端 .env 配置，无需填写';
                            }
                            if (!savedBaseUrl && envConfig.base_url) {
                                savedBaseUrl = envConfig.base_url;
                            }
                        }
                    } catch (e) {
                        console.error('加载 .env 配置失败:', e);
                    }
                }
                
                apiKeyInput.value = savedKey;
                apiBaseUrlInput.value = savedBaseUrl;
                
                // 显示默认 Base URL 提示
                const defaultUrls = {
                    'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                    'openai': 'https://api.openai.com/v1',
                    'volcengine': 'https://ark.cn-beijing.volces.com/api/v3',
                    'deepseek': 'https://api.deepseek.com',
                    'local': 'http://localhost:1234/v1'
                };
                
                if (!savedBaseUrl && defaultUrls[currentApiProvider]) {
                    apiBaseUrlInput.placeholder = `默认: ${defaultUrls[currentApiProvider]}`;
                }
                
                apiConfigModal.style.display = 'flex';
            });
        });

        closeApiConfigBtn.addEventListener('click', () => {
            apiConfigModal.style.display = 'none';
        });

        cancelApiConfigBtn.addEventListener('click', () => {
            apiConfigModal.style.display = 'none';
        });

        saveApiConfigBtn.addEventListener('click', () => {
            if (currentApiProvider) {
                // 保存到 localStorage
                localStorage.setItem(`${currentApiProvider}_api_key`, apiKeyInput.value);
                localStorage.setItem(`${currentApiProvider}_base_url`, apiBaseUrlInput.value);
                
                // 更新状态显示
                loadApiStatus();
                
                apiConfigModal.style.display = 'none';
                alert('API 配置已保存');
            }
        });

        // 提示词编辑相关
        const promptEditModal = document.getElementById('promptEditModal');
        const closePromptEditBtn = document.getElementById('closePromptEditBtn');
        const cancelPromptEditBtn = document.getElementById('cancelPromptEditBtn');
        const savePromptEditBtn = document.getElementById('savePromptEditBtn');
        const resetPromptBtn = document.getElementById('resetPromptBtn');
        const previewPromptBtn = document.getElementById('previewPromptBtn');
        const promptTextarea = document.getElementById('promptTextarea');
        const promptEditTitle = document.getElementById('promptEditTitle');
        let currentScenario = '';

        // 场景名称映射
        const scenarioNames = {
            'operation_guide': '操作指导场景',
            'fault_diagnosis': '故障诊断场景',
            'safety_regulation': '安全规范场景',
            'code_debug': '代码调试场景'
        };

        // 提示词编辑按钮点击
        document.querySelectorAll('.prompt-edit-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                currentScenario = btn.dataset.scenario;
                promptEditTitle.textContent = `编辑 ${scenarioNames[currentScenario]}`;
                
                // 显示加载状态
                promptTextarea.value = '正在加载...';
                promptTextarea.disabled = true;
                
                // 从后端加载当前提示词
                try {
                    const response = await fetch(`/api/scenario/prompt?scenario=${currentScenario}`);
                    const data = await response.json();
                    
                    if (data.success && data.prompt) {
                        promptTextarea.value = data.prompt;
                    } else {
                        promptTextarea.value = '# 加载失败\n\n请点击"恢复默认"获取默认提示词';
                    }
                } catch (e) {
                    console.error('加载提示词失败:', e);
                    promptTextarea.value = '# 加载失败\n\n' + e.message;
                } finally {
                    promptTextarea.disabled = false;
                }
                
                promptEditModal.style.display = 'flex';
            });
        });

        closePromptEditBtn.addEventListener('click', () => {
            promptEditModal.style.display = 'none';
        });

        cancelPromptEditBtn.addEventListener('click', () => {
            promptEditModal.style.display = 'none';
        });

        savePromptEditBtn.addEventListener('click', async () => {
            if (currentScenario) {
                // 禁用按钮，显示保存中
                savePromptEditBtn.disabled = true;
                savePromptEditBtn.textContent = '保存中...';
                
                try {
                    // 保存到后端
                    const response = await fetch('/api/scenario/prompt', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            scenario: currentScenario,
                            prompt: promptTextarea.value
                        })
                    });
                    
                    if (response.ok) {
                        promptEditModal.style.display = 'none';
                        alert('提示词已保存');
                        // 重新加载场景提示词预览
                        loadScenarioPrompts();
                    } else {
                        alert('保存失败，请重试');
                    }
                } catch (e) {
                    console.error('保存提示词失败:', e);
                    alert('保存失败，请检查网络连接');
                } finally {
                    savePromptEditBtn.disabled = false;
                    savePromptEditBtn.textContent = '保存';
                }
            }
        });

        resetPromptBtn.addEventListener('click', async () => {
            if (confirm('确定要恢复默认提示词吗？当前的修改将会丢失。')) {
                // 禁用按钮
                resetPromptBtn.disabled = true;
                resetPromptBtn.textContent = '加载中...';
                
                try {
                    // 从后端获取默认提示词
                    const response = await fetch(`/api/scenario/prompt/default?scenario=${currentScenario}`);
                    const data = await response.json();
                    
                    if (data.success && data.prompt) {
                        promptTextarea.value = data.prompt;
                        alert('已恢复默认提示词，请点击"保存"应用更改');
                    } else {
                        alert('加载失败，请重试');
                    }
                } catch (e) {
                    console.error('加载默认提示词失败:', e);
                    alert('加载失败，请重试');
                } finally {
                    resetPromptBtn.disabled = false;
                    resetPromptBtn.textContent = '恢复默认';
                }
            }
        });

        previewPromptBtn.addEventListener('click', () => {
            // 在新窗口中预览提示词
            const previewWindow = window.open('', '_blank', 'width=800,height=600');
            if (previewWindow) {
                previewWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>提示词预览 - ${scenarioNames[currentScenario]}</title>
                        <meta charset="UTF-8">
                        <style>
                            body {
                                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                                padding: 20px;
                                line-height: 1.6;
                                max-width: 800px;
                                margin: 0 auto;
                                background: #f5f5f5;
                            }
                            .container {
                                background: white;
                                padding: 30px;
                                border-radius: 8px;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            }
                            h1 {
                                color: #333;
                                border-bottom: 2px solid #0066ff;
                                padding-bottom: 10px;
                                margin-bottom: 20px;
                            }
                            pre {
                                background: #f5f5f5;
                                padding: 15px;
                                border-radius: 6px;
                                overflow-x: auto;
                                white-space: pre-wrap;
                                word-wrap: break-word;
                                border-left: 4px solid #0066ff;
                            }
                            .meta {
                                color: #666;
                                font-size: 14px;
                                margin-bottom: 20px;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>${scenarioNames[currentScenario]}</h1>
                            <div class="meta">
                                字符数: ${promptTextarea.value.length} | 
                                行数: ${promptTextarea.value.split('\n').length}
                            </div>
                            <pre>${promptTextarea.value.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                        </div>
                    </body>
                    </html>
                `);
                previewWindow.document.close();
            }
        });

        /*
        saveSettingsBtn.addEventListener('click', () => {
            localStorage.setItem('apiBaseUrl', apiBaseUrlInput.value);
            localStorage.setItem('apiKey', apiKeyInput.value);
            settingsModal.style.display = 'none';
            // Optional: Show a toast notification
            alert('设置已保存');
        });
        */

        // Model Config Modal Logic
        modelConfigBtn.addEventListener('click', () => {
            modelConfigModal.style.display = 'flex';
        });

        closeModelConfigBtn.addEventListener('click', () => {
            modelConfigModal.style.display = 'none';
        });

        saveModelConfigBtn.addEventListener('click', async () => {
            localStorage.setItem('selectedModel', llmSelect.value);
            localStorage.setItem('selectedOcrModel', ocrSelect.value);
            localStorage.setItem('selectedAsrModel', asrSelect.value);
            localStorage.setItem('selectedTtsModel', ttsSelect.value);
            
            // 保存系统提示词到后端
            try {
                await fetch('/api/system_prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ default: systemPromptInput.value })
                });
            } catch (e) {
                console.warn('保存系统提示词失败', e);
            }
            
            modelConfigModal.style.display = 'none';
            alert('模型配置已更新');
        });

        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === settingsModal) {
                settingsModal.style.display = 'none';
            }
            if (e.target === modelConfigModal) {
                modelConfigModal.style.display = 'none';
            }
            if (e.target === providerConfigModal) {
                providerConfigModal.style.display = 'none';
            }
            if (e.target === apiConfigModal) {
                apiConfigModal.style.display = 'none';
            }
            if (e.target === promptEditModal) {
                promptEditModal.style.display = 'none';
            }
        });

        // 1. 侧边栏收起/展开功能
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });

        // 2. 导航切换功能
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                
                // 获取目标
                const target = item.getAttribute('data-target');
                const href = item.getAttribute('href');
                
                // 如果是 IDE 链接，显示 IDE 界面
                if (item.id === 'ideNavItem' || target === 'ide') {
                    // 阻止默认行为
                    e.preventDefault();
                    
                    // 移除所有激活状态
                    navItems.forEach(nav => nav.classList.remove('active'));
                    // 激活当前
                    item.classList.add('active');
                    
                    // 隐藏聊天界面，显示 IDE 界面
                    chatHome.style.display = 'none';
                    featureInterface.style.display = 'flex';
                    
                    // 加载 IDE 内容
                    loadIDEInterface();
                    return;
                }
                
                // 移除所有激活状态
                navItems.forEach(nav => nav.classList.remove('active'));
                // 激活当前
                item.classList.add('active');

                // 获取功能名称
                const title = item.querySelector('span').textContent;
                const iconClass = item.querySelector('i').className;
                
                // 设置当前问答类型
                currentChatType = target;
                currentSessionId = ''; // 切换类型时重置会话

                // 切换显示到聊天并注入问候
                chatHome.style.display = 'flex';
                featureInterface.style.display = 'none';
                greetingContainer.style.display = 'none';
                chatList.style.display = 'flex';
                chatList.innerHTML = '';
                const greetText = pickFeatureGreeting(target);
                appendMessage(greetText, 'bot');
                setGreeting();
            });
        });

        // 3. 新对话按钮 - 返回主页
        newChatBtn.addEventListener('click', () => {
            navItems.forEach(nav => nav.classList.remove('active'));
            chatHome.style.display = 'flex';
            featureInterface.style.display = 'none';
            
            // 重置回问候界面
            greetingContainer.style.display = 'block';
            chatList.style.display = 'none';
            chatList.innerHTML = ''; // 清空聊天记录
            
            // 重置会话ID和问答类型
            currentSessionId = '';
            currentChatType = '';
            // 刷新历史列表（去掉高亮）
            renderHistory(historyCache);
            
            setGreeting();
        });

        // 4. 输入框逻辑
        inputArea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
            if (this.value.trim().length > 0) {
                sendBtn.classList.add('active');
            } else {
                sendBtn.classList.remove('active');
            }
        });

        // 发送消息核心逻辑
        async function sendMessage() {
            const text = inputArea.value.trim();
            // 如果没有文字也没有待发送的文件，则不发送
            if (!text && !pendingFile) return;
            
            // 如果是新会话且没有 session_id，生成一个新的
            if (!currentSessionId) {
                currentSessionId = generateUUID();
            }

            // 1. 界面状态切换：隐藏问候语和技能按钮，显示聊天列表
            greetingContainer.style.display = 'none';
            chatList.style.display = 'flex';

            // 2. 添加用户消息到界面
            const displayText = text || (pendingFile ? `[发送${pendingFile.type.startsWith('image') ? '图片' : '文件'}]` : '');
            appendMessage(displayText, 'user');

            // 获取当前配置
            const selectedModelRaw = localStorage.getItem('selectedModel') || '';
            let selectedModel = 'gpt-3.5-turbo';
            let selectedProvider = '';
            try {
                if (selectedModelRaw.trim().startsWith('{')) {
                    const parsed = JSON.parse(selectedModelRaw);
                    selectedModel = parsed.model || selectedModel;
                    selectedProvider = parsed.provider || '';
                } else if (selectedModelRaw) {
                    selectedModel = selectedModelRaw;
                }
            } catch (e) {
                console.warn('解析 selectedModel 失败，使用默认', e);
            }
            // 系统提示词由后端管理，前端不再传递
            const systemPrompt = '';
            
            // 简单的模型到供应商映射
            let providerId = selectedProvider || 'local';
            if (!selectedProvider) {
                if (selectedModel.includes('gpt')) providerId = 'local';
                if (selectedModel.includes('claude')) providerId = 'moonshot';
                if (selectedModel.includes('deepseek')) providerId = 'deepseek';
            }
            
            // 获取供应商配置
            const apiKey = localStorage.getItem(`provider_key_${providerId}`) || '';
            const baseUrl = localStorage.getItem(`provider_url_${providerId}`) || '';

            const botBubble = appendMessage('', 'bot', true, null, null, {
                model: selectedModel,
                timestamp: new Date().toISOString()
            }); // 先占位，后续流式填充
            let fullText = ''; // 累积文本用于 Markdown 解析
            
            // 清空输入框
            inputArea.value = '';
            inputArea.style.height = 'auto';
            sendBtn.classList.remove('active');

            // 3. 发送请求给后端（流式）
            try {
                let response;
                let kbSources = []; // 知识库来源信息（提升到外层作用域）
                
                if (pendingFile) {
                    // 有文件：使用 FormData 调用 /api/chat_with_file
                    const formData = new FormData();
                    formData.append('file', pendingFile);
                    
                    // 根据文件类型设置默认提示
                    const isImage = pendingFile.type && pendingFile.type.startsWith('image');
                    const defaultPrompt = isImage ? '请描述这张图片' : '请总结这个文件的内容';
                    formData.append('message', text || defaultPrompt);
                    
                    formData.append('model', selectedModel);
                    formData.append('system_prompt', systemPrompt);
                    formData.append('api_key', apiKey);
                    formData.append('base_url', baseUrl);
                    formData.append('provider_id', providerId);
                    formData.append('session_id', currentSessionId);
                    
                    console.log('[sendMessage] 发送文件:', pendingFile.name, '类型:', pendingFile.type);
                    
                    response = await fetch('/api/chat_with_file', {
                        method: 'POST',
                        body: formData
                    });
                    
                    // 清除待发送文件
                    pendingFile = null;
                } else {
                    // 无文件：使用 JSON 调用 /api/chat_stream
                    // 如果有问答类型，先检索知识库
                    let finalMessage = text;
                    let kbContext = '';
                    
                    if (currentChatType) {
                        try {
                            const kbRes = await fetch('/api/kb/search', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    query: text,
                                    kb_type: currentChatType,
                                    top_k: 3,
                                    threshold: 0.3
                                })
                            });
                            const kbData = await kbRes.json();
                            
                            if (kbData.success && kbData.results && kbData.results.length > 0) {
                                // 保存来源信息用于显示
                                kbSources = kbData.results.map((r, i) => ({
                                    index: i + 1,
                                    source: r.file || '未知来源',
                                    score: r.score ? (r.score * 100).toFixed(1) : '0',
                                    content: r.content ? r.content.substring(0, 100) + '...' : ''
                                }));
                                
                                kbContext = kbData.results.map((r, i) => 
                                    `[参考${i+1}] ${r.content}`
                                ).join('\n\n');
                                
                                finalMessage = `请根据以下参考资料回答用户问题。如果参考资料中没有相关信息，请基于你的知识回答。

参考资料：
${kbContext}

用户问题：${text}`;
                            }
                        } catch (kbErr) {
                            console.warn('知识库检索失败:', kbErr);
                        }
                    }
                    
                    response = await fetch('/api/chat_stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: finalMessage,
                            original_message: text,  // 保存用户原始输入用于历史记录
                            model: selectedModel,
                            system_prompt: systemPrompt,
                            api_key: apiKey,
                            base_url: baseUrl,
                            provider_id: providerId,
                            session_id: currentSessionId,
                            kb_sources: kbSources,  // 保存知识库来源到历史记录
                            enable_thinking: localStorage.getItem('chatMode') === 'think',  // 思考模式
                            enable_web_search: localStorage.getItem('toggle_online') === 'true'  // 联网搜索
                        })
                    });
                }

                if (!response.body) {
                    const contentDiv = botBubble.querySelector('.message-content') || botBubble;
                    contentDiv.textContent = '后端未返回流式响应';
                    return;
                }
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let done = false;

                while (!done) {
                    const { value, done: doneReading } = await reader.read();
                    done = doneReading;
                    if (value) {
                        const chunk = decoder.decode(value, { stream: !done });
                        fullText += chunk;
                        const contentDiv = botBubble.querySelector('.message-content') || botBubble;
                        
                        // 处理思考内容
                        const isThinkMode = localStorage.getItem('chatMode') === 'think';
                        let displayText = fullText;
                        
                        if (isThinkMode && fullText.includes('<think>')) {
                            // 解析思考内容和正式回复
                            const thinkMatch = fullText.match(/<think>([\s\S]*?)(<\/think>|$)/);
                            const thinkContent = thinkMatch ? thinkMatch[1] : '';
                            const thinkEnded = fullText.includes('</think>');
                            const mainContent = thinkEnded ? fullText.split('</think>')[1] || '' : '';
                            
                            let html = '';
                            if (thinkContent) {
                                const thinkingClass = thinkEnded ? 'thinking-block thinking-block-collapsed' : 'thinking-block';
                                html += `<div class="${thinkingClass}" onclick="this.classList.toggle('expanded');this.classList.toggle('thinking-block-collapsed')">${marked.parse(thinkContent)}</div>`;
                            }
                            if (mainContent.trim()) {
                                html += marked.parse(mainContent);
                            } else if (!thinkEnded) {
                                // 还在思考中，显示加载提示
                                html += '<span class="thinking-indicator">思考中...</span>';
                            }
                            contentDiv.innerHTML = html;
                        } else {
                            // 非思考模式或没有思考标签，直接渲染
                            contentDiv.innerHTML = marked.parse(displayText);
                        }
                        chatList.scrollTop = chatList.scrollHeight;
                    }
                }
                
                // 流式输出完成后处理代码块
                processCodeBlocks(botBubble);
                
                // 如果有知识库来源，在回复下方显示
                if (kbSources.length > 0) {
                    const sourceDiv = createKbSourcesElement(kbSources);
                    botBubble.parentElement.appendChild(sourceDiv);
                    chatList.scrollTop = chatList.scrollHeight;
                }
                
                loadHistory();
            } catch (error) {
                console.error('Error:', error);
                const contentDiv = botBubble.querySelector('.message-content') || botBubble;
                contentDiv.textContent = '无法连接到服务器，请检查后端是否启动。';
            }
        }

        // 创建知识库来源元素（支持收起/展开）
        function createKbSourcesElement(kbSources, collapsed = false) {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'kb-sources' + (collapsed ? ' collapsed' : '');
            sourceDiv.innerHTML = `
                <div class="kb-sources-header">
                    <span class="kb-sources-icon">📚</span>
                    <span>知识库来源 (${kbSources.length})</span>
                    <span class="kb-sources-toggle">${collapsed ? '▶' : '▼'}</span>
                </div>
                <div class="kb-sources-list">
                    ${kbSources.map(s => `
                        <div class="kb-source-item" title="${s.content || ''}">
                            <span class="kb-source-index">[${s.index}]</span>
                            <span class="kb-source-name">${s.source}</span>
                            <span class="kb-source-score">相似度: ${s.score}%</span>
                        </div>
                    `).join('')}
                </div>
            `;
            // 点击 header 切换收起/展开
            const header = sourceDiv.querySelector('.kb-sources-header');
            header.addEventListener('click', () => {
                sourceDiv.classList.toggle('collapsed');
                const toggle = sourceDiv.querySelector('.kb-sources-toggle');
                toggle.textContent = sourceDiv.classList.contains('collapsed') ? '▶' : '▼';
            });
            return sourceDiv;
        }

        function appendMessage(text, sender, returnBubble = false, kbSources = null, fileInfo = null, modelInfo = null) {
            const row = document.createElement('div');
            row.classList.add('message-row', sender);
            
            const bubble = document.createElement('div');
            bubble.classList.add('message-bubble', sender === 'user' ? 'user-bubble' : 'bot-bubble');
            
            // 如果是用户消息且有文件，先显示文件预览
            if (sender === 'user' && fileInfo && fileInfo.url) {
                const ext = fileInfo.filename.split('.').pop().toLowerCase();
                const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext);
                const isVideo = ['mp4', 'avi', 'mov', 'webm', 'flv'].includes(ext);
                
                let fileHtml = '';
                if (isImage) {
                    fileHtml = `<div class="message-file-preview">
                        <img src="${fileInfo.url}" alt="${fileInfo.filename}" onclick="window.open('${fileInfo.url}', '_blank')">
                    </div>`;
                } else if (isVideo) {
                    fileHtml = `<div class="message-file-preview">
                        <video controls src="${fileInfo.url}" style="max-width:300px;max-height:200px;border-radius:8px;"></video>
                    </div>`;
                } else {
                    fileHtml = `<div class="message-file-preview">
                        <a href="${fileInfo.url}" target="_blank" class="file-link">📎 ${fileInfo.filename}</a>
                    </div>`;
                }
                bubble.innerHTML = fileHtml + (text ? `<div class="message-text">${text}</div>` : '');
            } else if (sender === 'bot') {
                let contentHtml = '';
                if (text) {
                    contentHtml = marked.parse(text);
                }
                
                let headerHtml = '';
                if (modelInfo) {
                    const timeStr = modelInfo.timestamp ? new Date(modelInfo.timestamp).toLocaleString() : '';
                    const modelStr = modelInfo.model || 'AI Assistant';
                    headerHtml = `<div class="message-info" style="font-size: 12px; color: #86909c; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 500;">${modelStr}</span>
                        <span style="font-size: 11px; opacity: 0.8;">${timeStr}</span>
                    </div>`;
                }
                
                bubble.innerHTML = headerHtml + `<div class="message-content">${contentHtml}</div>`;
            } else {
                bubble.textContent = text;
            }
            
            row.appendChild(bubble);
            
            // 如果有知识库来源，添加到消息下方（历史记录加载时默认收起）
            if (kbSources && kbSources.length > 0) {
                const sourceDiv = createKbSourcesElement(kbSources, true);
                row.appendChild(sourceDiv);
            }
            
            chatList.appendChild(row);
            
            // 处理代码块：添加语言标签和复制按钮
            if (sender === 'bot') {
                processCodeBlocks(bubble);
            }
            
            // 滚动到底部
            chatList.scrollTop = chatList.scrollHeight;
            if (returnBubble) return bubble;
        }
        
        // 处理代码块：添加语言标签和复制按钮
        function processCodeBlocks(container) {
            const preBlocks = container.querySelectorAll('pre');
            preBlocks.forEach(pre => {
                // 避免重复处理
                if (pre.querySelector('.code-block-header')) return;
                
                const code = pre.querySelector('code');
                if (!code) return;
                
                // 获取语言
                let lang = 'code';
                const classList = code.className.split(' ');
                for (const cls of classList) {
                    if (cls.startsWith('language-') || cls.startsWith('hljs ')) {
                        const match = cls.match(/language-(\w+)/);
                        if (match) {
                            lang = match[1];
                            break;
                        }
                    }
                }
                
                // 创建头部
                const header = document.createElement('div');
                header.className = 'code-block-header';
                header.innerHTML = `
                    <span class="code-lang">${lang}</span>
                    <div class="code-actions">
                        <button class="code-action-btn copy-btn" title="复制代码">
                            <i class="ri-file-copy-line"></i>
                            <span>复制</span>
                        </button>
                    </div>
                `;
                
                // 插入头部
                pre.insertBefore(header, pre.firstChild);
                
                // 复制功能
                const copyBtn = header.querySelector('.copy-btn');
                copyBtn.addEventListener('click', async () => {
                    try {
                        await navigator.clipboard.writeText(code.textContent);
                        copyBtn.innerHTML = '<i class="ri-check-line"></i><span>已复制</span>';
                        copyBtn.classList.add('copied');
                        setTimeout(() => {
                            copyBtn.innerHTML = '<i class="ri-file-copy-line"></i><span>复制</span>';
                            copyBtn.classList.remove('copied');
                        }, 2000);
                    } catch (err) {
                        console.error('复制失败:', err);
                    }
                });
            });
        }

        sendBtn.addEventListener('click', sendMessage);

        inputArea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (inputArea.value.trim()) {
                    sendMessage();
                }
            }
        });

        // 语音按钮：点一下开始，再点一下暂停（仅状态展示，占位逻辑）
        // 语音录制相关
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;

        voiceBtn.addEventListener('click', async () => {
            if (isRecording) {
                stopRecording();
            } else {
                await startRecording();
            }
        });

        function updateVoiceUI() {
            if (isRecording) {
                voiceBtn.classList.add('voice-active');
                voiceBtn.title = '停止录音';
                voiceBtn.innerHTML = '<i class="ri-stop-circle-line"></i>';
                voiceStatus.classList.add('active');
            } else {
                voiceBtn.classList.remove('voice-active');
                voiceBtn.title = '语音';
                voiceBtn.innerHTML = '<i class="ri-mic-line"></i>';
                voiceStatus.classList.remove('active');
            }
        }

        attachBtn.addEventListener('click', () => {
            hiddenFileInput.value = '';
            hiddenFileInput.click();
        });

        hiddenFileInput.addEventListener('change', async () => {
            const file = hiddenFileInput.files[0];
            if (!file) return;
            await handleFileUpload(file);
        });

        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = [];
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) audioChunks.push(e.data);
                };
                mediaRecorder.onstop = async () => {
                    const blob = new Blob(audioChunks, { type: 'audio/webm' });
                    await uploadAudioBlob(blob);
                    stream.getTracks().forEach(t => t.stop());
                };
                mediaRecorder.start();
                isRecording = true;
                updateVoiceUI();
            } catch (err) {
                console.error('无法访问麦克风', err);
                alert('无法访问麦克风，请检查权限设置');
            }
        }

        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                updateVoiceUI();
            }
        }

        async function uploadAudioBlob(blob) {
            const formData = new FormData();
            const filename = `record_${Date.now()}.webm`;
            formData.append('file', blob, filename);
            
            // Add provider_id from selectedAsrModel
            const asrModelRaw = localStorage.getItem('selectedAsrModel');
            if (asrModelRaw) {
                try {
                    const parsed = JSON.parse(asrModelRaw);
                    if (parsed.provider) {
                        formData.append('provider_id', parsed.provider);
                    }
                } catch (e) {
                    console.warn('解析 selectedAsrModel 失败', e);
                }
            }

            try {
                const res = await fetch('/api/asr', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.error) {
                    appendMessage('语音识别失败: ' + data.error, 'bot');
                } else {
                    // 将识别结果填入输入框，而不是直接显示
                    inputArea.value = data.text;
                    inputArea.style.height = 'auto';
                    inputArea.style.height = (inputArea.scrollHeight) + 'px';
                    sendBtn.classList.add('active');
                    inputArea.focus();
                }
            } catch (err) {
                console.error(err);
                appendMessage('语音上传出错', 'bot');
            }
        }

        async function handleFileUpload(file) {
            const isAudio = file.type && file.type.startsWith('audio');
            
            // 音频文件直接上传进行语音识别
            if (isAudio) {
                const formData = new FormData();
                formData.append('file', file);
                
                // Add provider_id from selectedAsrModel
                const asrModelRaw = localStorage.getItem('selectedAsrModel');
                if (asrModelRaw) {
                    try {
                        const parsed = JSON.parse(asrModelRaw);
                        if (parsed.provider) {
                            formData.append('provider_id', parsed.provider);
                        }
                    } catch (e) {
                        console.warn('解析 selectedAsrModel 失败', e);
                    }
                }

                try {
                    const res = await fetch('/api/asr', { method: 'POST', body: formData });
                    const data = await res.json();
                    if (data.error) {
                        appendMessage('上传失败: ' + data.error, 'bot');
                    } else {
                        appendMessage(`语音转写完成：${data.text}`, 'bot');
                    }
                    loadHistory();
                } catch (err) {
                    console.error(err);
                    appendMessage('上传过程中出错', 'bot');
                }
                return;
            }
            
            // 图片/文档文件：保存待发送，显示预览提示
            pendingFile = file;
            const isImage = file.type && file.type.startsWith('image');
            const fileType = isImage ? '图片' : '文件';
            
            // 显示文件预览提示
            greetingContainer.style.display = 'none';
            chatList.style.display = 'flex';
            
            let previewHtml = `📎 已选择${fileType}：${file.name}`;
            if (isImage) {
                // 图片预览
                const reader = new FileReader();
                reader.onload = (e) => {
                    const previewMsg = `📎 已选择图片：${file.name}<br><img src="${e.target.result}" style="max-width:200px;max-height:150px;border-radius:8px;margin-top:8px;">`;
                    appendMessage(previewMsg + '<br><span style="color:#86909c;font-size:12px;">请输入问题后发送，或直接发送让AI描述图片</span>', 'bot');
                };
                reader.readAsDataURL(file);
            } else {
                appendMessage(previewHtml + '<br><span style="color:#86909c;font-size:12px;">请输入问题后发送</span>', 'bot');
            }
            
            // 激活发送按钮（即使没有文字也可以发送图片）
            sendBtn.classList.add('active');
        }
        // Knowledge Base Management Logic
        const kbManageBtn = document.getElementById('kbManageBtn');
        const kbModal = document.getElementById('kbModal');
        const kbTabs = document.querySelectorAll('.kb-tab');
        const kbAddFileBtn = document.getElementById('kbAddFileBtn'); 
        const kbFileInput = document.getElementById('kbFileInput');
        const kbTableBody = document.getElementById('kbTableBody'); 
        const kbTotalCount = document.getElementById('kbTotalCount');
        const kbCurrentTitle = document.getElementById('kbCurrentTitle');
        const closeKbModalBtn = kbModal.querySelector('.close-modal');
        let currentKbType = 'guide';  // 默认显示操作指导知识库

        // New Elements
        const kbParseSettingsBtn = document.getElementById('kbParseSettingsBtn');
        const kbRetrievalSettingsBtn = document.getElementById('kbRetrievalSettingsBtn');
        const kbRecallTestBtn = document.getElementById('kbRecallTestBtn');
        
        const parseSettingsModal = document.getElementById('parseSettingsModal');
        const retrievalSettingsModal = document.getElementById('retrievalSettingsModal');
        const recallTestModal = document.getElementById('recallTestModal');

        const saveParseSettingsBtn = document.getElementById('saveParseSettingsBtn');
        const saveRetrievalSettingsBtn = document.getElementById('saveRetrievalSettingsBtn');
        const startRecallTestBtn = document.getElementById('startRecallTestBtn');
        const recallTestInput = document.getElementById('recallTestInput');
        const recallTestResults = document.getElementById('recallTestResults');

        // Initialize Settings from LocalStorage
        (function initSettings() {
            // Parse Settings
            try {
                const parseSettings = JSON.parse(localStorage.getItem('kbParseSettings') || '{}');
                if (parseSettings.ocr) document.getElementById('parseOcrTool').value = parseSettings.ocr;
                if (parseSettings.strategy) document.getElementById('parseSplitStrategy').value = parseSettings.strategy;
                if (parseSettings.chunkSize) document.getElementById('parseChunkSize').value = parseSettings.chunkSize;
                if (parseSettings.overlap) document.getElementById('parseOverlap').value = parseSettings.overlap;
            } catch (e) { console.error('Failed to load parse settings', e); }

            // Retrieval Settings
            try {
                const retrievalSettings = JSON.parse(localStorage.getItem('kbRetrievalSettings') || '{}');
                if (retrievalSettings.topK) document.getElementById('retrievalTopK').value = retrievalSettings.topK;
                if (retrievalSettings.threshold) {
                    const threshold = retrievalSettings.threshold;
                    const el = document.getElementById('retrievalThreshold');
                    const valEl = document.getElementById('retrievalThresholdVal');
                    if (el && valEl) {
                        el.value = threshold;
                        valEl.textContent = threshold;
                    }
                }
            } catch (e) { console.error('Failed to load retrieval settings', e); }
        })();

        // Toggle chunk size and overlap fields based on split strategy
        const parseSplitStrategy = document.getElementById('parseSplitStrategy');
        const chunkSizeGroup = document.getElementById('chunkSizeGroup');
        const overlapGroup = document.getElementById('overlapGroup');
        
        function updateChunkFieldsVisibility() {
            const strategy = parseSplitStrategy.value;
            // smart 和 fixed_size 都显示 chunk size 和 overlap 设置
            const showChunkSettings = ['smart', 'fixed_size', 'recursive', 'hybrid'].includes(strategy);
            chunkSizeGroup.style.display = showChunkSettings ? 'block' : 'none';
            overlapGroup.style.display = ['smart', 'fixed_size'].includes(strategy) ? 'block' : 'none';
        }
        
        // Listen for strategy changes
        parseSplitStrategy.addEventListener('change', updateChunkFieldsVisibility);
        
        // Initialize visibility on page load (after settings are loaded)
        setTimeout(updateChunkFieldsVisibility, 0);

        const retrievalThreshold = document.getElementById('retrievalThreshold');
        const retrievalThresholdVal = document.getElementById('retrievalThresholdVal');

        // Modal Toggles
        function setupModalToggle(btn, modal) {
            btn.addEventListener('click', () => {
                modal.style.display = 'flex';
            });
            const closeBtn = modal.querySelector('.close-modal');
            if(closeBtn) {
                closeBtn.addEventListener('click', () => {
                    modal.style.display = 'none';
                });
            }
        }

        setupModalToggle(kbParseSettingsBtn, parseSettingsModal);
        setupModalToggle(kbRetrievalSettingsBtn, retrievalSettingsModal);
        setupModalToggle(kbRecallTestBtn, recallTestModal);

        // Threshold Slider
        retrievalThreshold.addEventListener('input', (e) => {
            retrievalThresholdVal.textContent = e.target.value;
        });

        // Save Settings (Mock)
        saveParseSettingsBtn.addEventListener('click', () => {
            const settings = {
                ocr: document.getElementById('parseOcrTool').value,
                strategy: document.getElementById('parseSplitStrategy').value,
                chunkSize: document.getElementById('parseChunkSize').value,
                overlap: document.getElementById('parseOverlap').value
            };
            localStorage.setItem('kbParseSettings', JSON.stringify(settings));
            parseSettingsModal.style.display = 'none';
            alert('解析设置已保存');
        });

        saveRetrievalSettingsBtn.addEventListener('click', () => {
             const settings = {
                topK: document.getElementById('retrievalTopK').value,
                threshold: document.getElementById('retrievalThreshold').value
            };
            localStorage.setItem('kbRetrievalSettings', JSON.stringify(settings));
            retrievalSettingsModal.style.display = 'none';
            alert('检索设置已保存');
        });

        // Recall Test - 调用真实后端 API
        startRecallTestBtn.addEventListener('click', async () => {
            const query = recallTestInput.value.trim();
            if (!query) return;

            recallTestResults.innerHTML = '<div style="text-align:center;color:#666;">正在检索...</div>';
            
            // 获取检索设置
            const retrievalSettings = JSON.parse(localStorage.getItem('kbRetrievalSettings') || '{}');
            const topK = parseInt(retrievalSettings.topK) || 5;
            const threshold = parseFloat(retrievalSettings.threshold) || 0.0;
            
            try {
                const res = await fetch('/api/kb/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        kb_type: currentKbType,
                        top_k: topK,
                        threshold: threshold
                    })
                });
                
                const data = await res.json();
                
                if (data.success && data.results && data.results.length > 0) {
                    recallTestResults.innerHTML = data.results.map((r, i) => `
                        <div style="background: white; padding: 10px; margin-bottom: 10px; border: 1px solid #eee; border-radius: 4px;">
                            <div style="font-size: 14px; color: #333; margin-bottom: 5px; white-space: pre-wrap;">${r.content.substring(0, 300)}${r.content.length > 300 ? '...' : ''}</div>
                            <div style="font-size: 12px; color: #999; display: flex; justify-content: space-between;">
                                <span>来源: ${r.file}${r.title ? ' - ' + r.title : ''}</span>
                                <span style="color: var(--accent-color); font-weight: 500;">相似度: ${r.score.toFixed(4)}</span>
                            </div>
                        </div>
                    `).join('');
                } else if (data.success && (!data.results || data.results.length === 0)) {
                    recallTestResults.innerHTML = '<div style="text-align:center;color:#999;padding:20px;">未找到相关内容，请尝试其他关键词或降低相似度阈值</div>';
                } else {
                    recallTestResults.innerHTML = `<div style="text-align:center;color:#ff4d4f;padding:20px;">检索失败: ${data.error || '未知错误'}</div>`;
                }
            } catch (err) {
                console.error('Recall test error:', err);
                recallTestResults.innerHTML = `<div style="text-align:center;color:#ff4d4f;padding:20px;">检索出错: ${err.message}<br><small>请确保知识库索引已构建</small></div>`;
            }
        });

        const kbNameMap = {
            'guide': '操作指导知识库',
            'diagnosis': '故障诊断知识库',
            'safety': '安全规范知识库',
            'debug': '代码调试知识库'
        };

        kbManageBtn.addEventListener('click', () => {
            kbModal.style.display = 'flex';
            loadKbFiles(currentKbType);
            updateKbHeader(currentKbType);
        });

        function updateKbHeader(type) {
            kbCurrentTitle.textContent = kbNameMap[type] || '知识库';
        }

        closeKbModalBtn.addEventListener('click', () => {
            kbModal.style.display = 'none';
        });

        window.addEventListener('click', (e) => {
            if (e.target === kbModal) kbModal.style.display = 'none';
            if (e.target === parseSettingsModal) parseSettingsModal.style.display = 'none';
            if (e.target === retrievalSettingsModal) retrievalSettingsModal.style.display = 'none';
            if (e.target === recallTestModal) recallTestModal.style.display = 'none';
            if (e.target === settingsModal) settingsModal.style.display = 'none';
            if (e.target === modelConfigModal) modelConfigModal.style.display = 'none';
            if (e.target === providerConfigModal) providerConfigModal.style.display = 'none';
        });

        kbTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                kbTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentKbType = tab.dataset.kb;
                updateKbHeader(currentKbType);
                loadKbFiles(currentKbType);
            });
        });

        kbAddFileBtn.addEventListener('click', () => {
            kbFileInput.click();
        });

        kbFileInput.addEventListener('change', (e) => {
            handleKbFiles(e.target.files);
        });
        
        // 构建索引按钮
        const kbBuildIndexBtn = document.getElementById('kbBuildIndexBtn');
        kbBuildIndexBtn.addEventListener('click', async () => {
            if (!confirm(`确定要为"${kbNameMap[currentKbType]}"构建索引吗？\n这可能需要一些时间。`)) {
                return;
            }
            
            // 获取解析设置
            const parseSettings = JSON.parse(localStorage.getItem('kbParseSettings') || '{}');
            const chunkSize = parseInt(parseSettings.chunkSize) || 500;
            const chunkMethod = parseSettings.strategy || 'smart';  // 默认使用智能切分
            
            kbBuildIndexBtn.disabled = true;
            kbBuildIndexBtn.innerHTML = '<i class="ri-loader-4-line"></i> 构建中...';
            
            try {
                const res = await fetch('/api/kb/build', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        kb_type: currentKbType,
                        chunk_method: chunkMethod,
                        chunk_size: chunkSize
                    })
                });
                
                const data = await res.json();
                
                if (data.success) {
                    alert(`索引构建完成！\n共生成 ${data.total_docs} 个文档块`);
                    loadKbStatus(currentKbType);
                } else {
                    alert('构建失败: ' + (data.error || '未知错误'));
                }
            } catch (err) {
                console.error('Build index error:', err);
                alert('构建出错: ' + err.message);
            } finally {
                kbBuildIndexBtn.disabled = false;
                kbBuildIndexBtn.innerHTML = '<i class="ri-database-2-line"></i> 构建索引';
            }
        });
        
        // 删除按钮
        const kbDeleteBtn = document.getElementById('kbDeleteBtn');
        kbDeleteBtn.addEventListener('click', async () => {
            const checkboxes = kbTableBody.querySelectorAll('input[type="checkbox"]:checked');
            if (checkboxes.length === 0) {
                alert('请先选择要删除的文件');
                return;
            }
            
            if (!confirm(`确定要删除选中的 ${checkboxes.length} 个文件吗？`)) {
                return;
            }
            
            for (const checkbox of checkboxes) {
                const row = checkbox.closest('tr');
                const filename = row.querySelector('td:nth-child(2)').textContent;
                
                try {
                    await fetch('/api/kb/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            kb_type: currentKbType,
                            filename: filename
                        })
                    });
                } catch (err) {
                    console.error('Delete error:', err);
                }
            }
            
            loadKbFiles(currentKbType);
        });

        async function handleKbFiles(files) {
            if (!files || files.length === 0) return;
            
            const formData = new FormData();
            formData.append('kb_type', currentKbType);
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                // Show loading state in table
                kbTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:20px;">正在上传并处理...</td></tr>';
                
                const res = await fetch('/api/kb/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                if (data.success) {
                    alert(`上传成功: ${data.message}`);
                    loadKbFiles(currentKbType);
                } else {
                    alert('上传失败: ' + (data.error || '未知错误'));
                    loadKbFiles(currentKbType);
                }
            } catch (err) {
                console.error('Upload error', err);
                alert('上传出错: ' + err.message);
                loadKbFiles(currentKbType);
            }
        }

        async function loadKbFiles(type) {
            try {
                kbTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:20px;">加载中...</td></tr>';
                const res = await fetch(`/api/kb/files?type=${type}`);
                const data = await res.json();
                
                if (data.success) {
                    renderKbFiles(data.files);
                    // 同时加载知识库状态
                    loadKbStatus(type);
                } else {
                    kbTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:20px;color:red;">加载失败</td></tr>';
                }
            } catch (err) {
                console.warn('Load files error:', err);
                kbTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:20px;color:#999;">暂无文件</td></tr>';
                kbTotalCount.textContent = 0;
            }
        }
        
        async function loadKbStatus(type) {
            try {
                const res = await fetch(`/api/kb/status?type=${type}`);
                const data = await res.json();
                
                // 更新状态显示
                const statusInfo = document.getElementById('kbStatusInfo');
                if (statusInfo) {
                    if (data.index_exists && data.doc_count > 0) {
                        statusInfo.innerHTML = `<span style="color: #00b42a;"><i class="ri-checkbox-circle-fill"></i> 索引已构建 (${data.doc_count} 个文档块)</span>`;
                    } else if (data.file_count > 0) {
                        statusInfo.innerHTML = `<span style="color: #ff7d00;"><i class="ri-error-warning-fill"></i> 有 ${data.file_count} 个文件待构建索引</span>`;
                    } else {
                        statusInfo.innerHTML = `<span style="color: #999;"><i class="ri-information-fill"></i> 暂无文件</span>`;
                    }
                }
            } catch (err) {
                console.warn('Load KB status error:', err);
            }
        }

        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function renderKbFiles(files) {
            if (!files || files.length === 0) {
                kbTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:20px;color:#999;">暂无文件</td></tr>';
                kbTotalCount.textContent = 0;
                return;
            }
            
            kbTotalCount.textContent = files.length;
            kbTableBody.innerHTML = files.map(file => {
                // 根据状态显示不同的徽章
                let statusBadge = '';
                if (file.status === 'completed') {
                    statusBadge = '<span class="status-badge" style="color: #00b42a;"><i class="ri-checkbox-circle-fill"></i> 完成</span>';
                } else if (file.status === 'processing') {
                    statusBadge = '<span class="status-badge" style="color: #ff7d00;"><i class="ri-loader-4-line"></i> 处理中</span>';
                } else {
                    statusBadge = '<span class="status-badge" style="color: #86909c;"><i class="ri-time-line"></i> 待构建</span>';
                }
                
                return `
                <tr data-filename="${file.name}">
                    <td><input type="checkbox"></td>
                    <td style="color:var(--accent-color); font-weight:500;" title="${file.name}">${file.name.length > 30 ? file.name.substring(0, 30) + '...' : file.name}</td>
                    <td>${file.type || '文档'}</td>
                    <td>${file.chars || 0}</td>
                    <td>${file.recall || 0}</td>
                    <td>${file.date || '-'}</td>
                    <td>
                        <label class="toggle-switch">
                            <input type="checkbox" ${file.enabled !== false ? 'checked' : ''}>
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>${statusBadge}</td>
                    <td style="text-align: right;" class="table-actions">
                        <a class="delete" onclick="deleteKbFile('${file.name}')">删除</a>
                    </td>
                </tr>
            `}).join('');
        }
        
        // 删除单个文件
        async function deleteKbFile(filename) {
            if (!confirm(`确定要删除文件 "${filename}" 吗？`)) {
                return;
            }
            
            try {
                const res = await fetch('/api/kb/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        kb_type: currentKbType,
                        filename: filename
                    })
                });
                
                const data = await res.json();
                if (data.success) {
                    loadKbFiles(currentKbType);
                } else {
                    alert('删除失败: ' + (data.error || '未知错误'));
                }
            } catch (err) {
                console.error('Delete error:', err);
                alert('删除出错: ' + err.message);
            }
        }

