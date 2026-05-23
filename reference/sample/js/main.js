document.addEventListener('DOMContentLoaded', () => {
    // === DOM 元素获取 ===
    const themeSelector = document.getElementById('theme-selector');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar');
    const toggleRightSidebarBtn = document.getElementById('toggle-right-sidebar');
    const sidebar = document.getElementById('sidebar');
    const rightSidebar = document.getElementById('right-sidebar');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatContainer = document.getElementById('chat-container');
    const welcomeScreen = document.getElementById('welcome-screen');
    const categoryCards = document.querySelectorAll('.category-card');
    const newChatBtn = document.getElementById('new-chat-btn');
    const suggestionsBar = document.getElementById('suggestions-bar');
    const suggestionOptions = document.getElementById('suggestion-options');

    let isAgentAsking = false; // 是否处于Agent主动问询模式

    // === 主题切换逻辑 ===
    themeSelector.addEventListener('change', (e) => {
        const selectedTheme = e.target.value;
        // 移除所有特定的主题类
        document.body.className = '';
        // 加上选中的主体类
        document.body.classList.add(selectedTheme);
    });

    // === 侧边栏折叠逻辑 ===
    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('closed');
    });

    if(toggleRightSidebarBtn) {
        toggleRightSidebarBtn.addEventListener('click', () => {
            rightSidebar.classList.toggle('closed');
        });
    }

    // === 输入框自动扩展与发送按钮状态 ===
    userInput.addEventListener('input', function() {
        // 自动调整高度
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        // 发送按钮启用/禁用
        if (this.value.trim().length > 0) {
            sendBtn.removeAttribute('disabled');
        } else {
            sendBtn.setAttribute('disabled', 'true');
        }
    });

    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // === 新建对话 ===
    newChatBtn.addEventListener('click', () => {
        userInput.disabled = false;
        isAgentAsking = false;
        suggestionsBar.style.display = 'none';
        // 清理聊天记录，重新显示欢迎界面
        chatContainer.innerHTML = '';
        chatContainer.appendChild(welcomeScreen);
        welcomeScreen.style.display = 'block';
        userInput.value = '';
        userInput.style.height = 'auto';
        sendBtn.setAttribute('disabled', 'true');
    });

    // === 模板卡片点击逻辑 ===
    categoryCards.forEach(card => {
        card.addEventListener('click', () => {
            const category = card.getAttribute('data-category');
            let initialMessage = '';
            
            switch(category) {
                case 'research':
                    initialMessage = '我想进行深度研究。我的主要目标是理清技术逻辑与项目思路。';
                    break;
                case 'creative':
                    initialMessage = '我需要创意发散。请帮助我打破思维定势，协助产品设计。';
                    break;
                case 'emotion':
                    initialMessage = '我希望进行情感分析。我需要客观审视近期的心理状态。';
                    break;
                case 'decision':
                    initialMessage = '我面临决策分析的困难。请帮我权衡当下局面的利弊。';
                    break;
            }
            
            userInput.value = initialMessage;
            sendBtn.removeAttribute('disabled');
            sendMessage(); // 点击卡片后直接触发思考
        });
    });

    // === 发送消息逻辑 ===
    sendBtn.addEventListener('click', sendMessage);

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;
        
        // 无论如何，一旦发送消息，必定清除问询板状态
        exitAgentInquiryMode();

        // 1. 隐藏欢迎页面
        if (welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
        }

        // 2. 将用户消息添加到容器
        appendUserMessage(text);

        // 3. 重置输入框
        userInput.value = '';
        userInput.style.height = 'auto';
        sendBtn.setAttribute('disabled', 'true');

        // 4. 模拟AI通过"反问"引导的回复并进入问询模式
        setTimeout(() => {
            appendAIMessage("我能理解您的目标。为了更深入地切中要害，我想先问您：在您目前所处的状况下，最让您感到阻力或是困惑的核心点是什么？");
            enterAgentInquiryMode([
                "我不清楚如何开始第一步",
                "团队之间存在沟通障碍",
                "担心该决定带来长期的负面影响"
            ]);
        }, 800);
    }

    // === 问询模式(Plan模式) ===
    function enterAgentInquiryMode(options) {
        isAgentAsking = true;
        suggestionOptions.innerHTML = '';
        
        options.forEach(optText => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = optText;
            btn.addEventListener('click', () => {
                // 点击具体的建议时，填入输入框，解冻输入框但不立即发送，保留建议框以供可能更改
                userInput.value = optText;
                userInput.disabled = false;
                sendBtn.removeAttribute('disabled');
                
                // 调整高度
                userInput.style.height = 'auto';
                userInput.style.height = (userInput.scrollHeight) + 'px';
            });
            suggestionOptions.appendChild(btn);
        });

        // 增加"其他"选项
        const otherBtn = document.createElement('button');
        otherBtn.className = 'suggestion-btn other-btn';
        otherBtn.innerHTML = '<i class="fas fa-edit"></i> 其他想法...';
        otherBtn.addEventListener('click', () => {
            // 当点击其他时，不隐藏建议框，只解冻输入框并改变占位符
            userInput.disabled = false;
            userInput.focus();
            if(!userInput.value) {
                userInput.placeholder = "请输入您的具体想法，或再次点击上方的建议发送";
            }
        });
        suggestionOptions.appendChild(otherBtn);

        suggestionsBar.style.display = 'block';
        userInput.disabled = true; // 挂起普通输入，迫使用户先选择或点击其他
        userInput.placeholder = "请先选择上方的建议，或点击'其他想法...'";
    }

    function exitAgentInquiryMode() {
        isAgentAsking = false;
        suggestionsBar.style.display = 'none';
        userInput.disabled = false;
        userInput.placeholder = "说出您现在的想法或困惑...";
    }

    // === 辅助渲染函数 ===
    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message msg-user';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions user-actions';
        actionsDiv.innerHTML = `
            <button class="action-btn" title="复制"><i class="far fa-copy"></i></button>
            <button class="action-btn" title="编辑"><i class="far fa-edit"></i></button>
        `;
        
        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(actionsDiv);
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendAIMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message msg-ai';
        
        const wrapper = document.createElement('div');
        wrapper.className = 'ai-content-wrapper';
        wrapper.innerHTML = `<i class="fas fa-brain ai-avatar"></i><div class="message-content">${text}</div>`;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions ai-actions';
        actionsDiv.innerHTML = `
            <button class="action-btn" title="复制"><i class="far fa-copy"></i></button>
            <button class="action-btn" title="重新生成"><i class="fas fa-sync-alt"></i></button>
            <button class="action-btn" title="喜欢"><i class="far fa-thumbs-up"></i></button>
            <button class="action-btn" title="不喜欢"><i class="far fa-thumbs-down"></i></button>
            <button class="action-btn" title="分享"><i class="fas fa-share"></i></button>
        `;
        
        msgDiv.appendChild(wrapper);
        msgDiv.appendChild(actionsDiv);
        
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});