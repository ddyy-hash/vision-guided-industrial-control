async function testDeviceAPI() {
    try {
        console.log('正在测试设备API...');

        const response = await fetch('http://localhost:5000/api/devices');
        const data = await response.json();

        console.log('API响应状态:', response.status);
        console.log('API响应数据:', data);

        if (data.success && data.data) {
            console.log(`成功获取到 ${data.data.length} 个设备:`);
            data.data.forEach(device => {
                console.log(`- ${device.name} (${device.device_id}): ${device.device_type} - ${device.status}`);
            });
        } else {
            console.log('获取设备列表失败:', data.message);
        }

    } catch (error) {
        console.error('测试设备API时出错:', error);
    }
}

testDeviceAPI();