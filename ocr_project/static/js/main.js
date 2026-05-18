document.addEventListener('DOMContentLoaded', () => {
    // DOM 元素
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const processBtn = document.getElementById('processBtn');
    const previewImage = document.getElementById('previewImage');
    const imagePreview = document.getElementById('imagePreview');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const textOutput = document.getElementById('textOutput');
    const jsonOutput = document.getElementById('jsonOutput');
    const copyTextBtn = document.getElementById('copyTextBtn');
    const copyJsonBtn = document.getElementById('copyJsonBtn');
    const tabs = document.querySelectorAll('.tab');
    const toast = document.getElementById('toast');
    const energyLevelDisplay = document.getElementById('energyLevelDisplay');

    let currentFile = null;

    // 事件监听
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    processBtn.addEventListener('click', processImage);
    copyTextBtn.addEventListener('click', () => copyToClipboard(textOutput));
    copyJsonBtn.addEventListener('click', () => copyToClipboard(jsonOutput));

    // 拖放功能
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);

    // 标签切换
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // 移除所有活动标签
            tabs.forEach(t => t.classList.remove('active'));
            // 添加当前活动标签
            tab.classList.add('active');

            // 隐藏所有内容面板
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });

            // 显示对应内容面板
            const tabName = tab.getAttribute('data-tab');
            document.getElementById(`${tabName}Result`).classList.add('active');
        });
    });

    // 处理文件选择
    function handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            loadFile(files[0]);
        }
    }

    // 处理拖放文件
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            loadFile(files[0]);
        }
    }

    // 加载文件并显示预览
    function loadFile(file) {
        if (!file.type.match('image.*')) {
            showToast('请选择图片文件', 'error');
            return;
        }

        currentFile = file;

        // 显示预览
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            imagePreview.style.display = 'block';
        };
        reader.readAsDataURL(file);

        // 启用处理按钮
        processBtn.disabled = false;

        // 重置能耗等级显示
        energyLevelDisplay.textContent = "请上传能效标识图片";
        energyLevelDisplay.className = 'energy-level-display';
    }

    // 处理图片
    async function processImage() {
        if (!currentFile) return;

        // 显示加载状态
        loadingOverlay.classList.add('active');
        processBtn.disabled = true;

        // 重置能耗等级显示
        energyLevelDisplay.textContent = "正在识别能耗等级...";
        energyLevelDisplay.className = 'energy-level-display';

        try {
            // 创建FormData对象
            const formData = new FormData();
            formData.append('file', currentFile);

            // 同时发送OCR和能耗识别请求
            const [ocrResponse, energyResponse] = await Promise.all([
                fetch('/api/ocr/image', { method: 'POST', body: formData }),
                fetch('/api/energy/detect', { method: 'POST', body: formData })
            ]);

            // 处理OCR响应
            if (!ocrResponse.ok) {
                throw new Error(`OCR 处理失败: ${ocrResponse.status}`);
            }
            const ocrData = await ocrResponse.json();

            if (ocrData.result.code !== 100) {
                throw new Error(`OCR 错误: ${ocrData.result.message || '未知错误'}`);
            }

            // 处理能耗识别响应
            if (!energyResponse.ok) {
                throw new Error(`能耗识别失败: ${energyResponse.status}`);
            }
            const energyData = await energyResponse.json();

            if (energyData.code !== 100) {
                throw new Error(`能耗识别错误: ${energyData.message || '未知错误'}`);
            }

            // 显示结果
            displayResults(ocrData, energyData);
            showToast('识别成功!', 'success');

        } catch (error) {
            console.error('处理图像时出错:', error);
            showToast(error.message || '发生未知错误', 'error');
        } finally {
            // 隐藏加载状态
            loadingOverlay.classList.remove('active');
            processBtn.disabled = false;
        }
    }

    // 修改displayResults函数
    function displayResults(ocrData, energyData) {
        // 文本结果
        const keepFormatting = document.getElementById('keepFormatting').checked;
        let textResult = '';

        ocrData.result.data.forEach(item => {
            if (keepFormatting) {
                textResult += item.text + '\n';
            } else {
                textResult += item.text.replace(/\s+/g, '') + '\n';
            }
        });

        textOutput.value = textResult;

        // JSON 结果 - 包含OCR和能耗数据
        const combinedData = {
            ocr: ocrData,
            energy: energyData
        };
        jsonOutput.textContent = JSON.stringify(combinedData, null, 2);

        // 显示能耗等级
        displayEnergyLevel(energyData.data.energy_level);
        
        // 在控制台输出调试信息
        console.log('能耗检测详细数据:', {
            energy_level: energyData.data.energy_level,
            detected_color_count: energyData.data.detected_color_count,
            level_colors: energyData.data.level_colors,
            current_color: energyData.data.current_color,
            algorithm_version: energyData.data.algorithm_version
        });
    }

    // 修改displayEnergyLevel函数
    function displayEnergyLevel(level) {
        if (!level) {
            energyLevelDisplay.textContent = "未识别到能效等级";
            energyLevelDisplay.className = 'energy-level-display';
            return;
        }

        // 更 robust 的等级提取 - 支持多种格式
        let levelNum = '1';
        const levelMatch = level.match(/[1-5]/);
        if (levelMatch) {
            levelNum = levelMatch[0];
        } else {
            // 如果没有找到数字，尝试从字符串开头提取
            levelNum = level.charAt(0);
            // 验证是否为有效数字
            if (!['1', '2', '3', '4', '5'].includes(levelNum)) {
                levelNum = '1'; // 默认1级
            }
        }

        energyLevelDisplay.textContent = `识别结果: 能效等级 ${levelNum} 级`;
        energyLevelDisplay.className = 'energy-level-display';

        // 添加对应等级的样式类
        if (levelNum === '1') {
            energyLevelDisplay.classList.add('level-1');
        } else if (levelNum === '2') {
            energyLevelDisplay.classList.add('level-2');
        } else if (levelNum === '3') {
            energyLevelDisplay.classList.add('level-3');
        } else if (levelNum === '4') {
            energyLevelDisplay.classList.add('level-4');
        } else if (levelNum === '5') {
            energyLevelDisplay.classList.add('level-5');
        }
    }

    // 复制到剪贴板
    function copyToClipboard(element) {
        element.select();
        document.execCommand('copy');

        // 显示视觉反馈
        const originalText = element.value || element.textContent;
        const message = element === textOutput ? '文本已复制' : 'JSON 已复制';
        showToast(message, 'success');
    }

    // 显示提示
    function showToast(message, type = '') {
        toast.textContent = message;
        toast.className = 'toast show';

        if (type) {
            toast.classList.add(type);
        }

        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    }

    // 辅助函数
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropZone.classList.add('drag-over');
    }

    function unhighlight() {
        dropZone.classList.remove('drag-over');
    }
});