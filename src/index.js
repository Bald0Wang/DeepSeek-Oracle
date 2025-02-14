// node index.js

const express = require("express");
const { astro } = require("iztro");

const app = express();
const PORT = 3000;

// 解析 JSON 请求体
app.use(express.json());

// 创建一个 API 接口，通过阳历获取星盘信息
app.post("/api/astro/solar", (req, res) => {
    const { date, timezone, gender } = req.body;

    // 检查请求参数
    if (!date  || !gender) {
        return res.status(400).json({ error: "缺少必要的参数" });
    }

    try {
        // 通过阳历获取星盘信息
        const astrolabeSolar = astro.bySolar(date, timezone, gender);
        return res.json(astrolabeSolar);
    } catch (error) {
        return res.status(500).json({ error: "计算阳历星盘信息时出错" });
    }
});

// 创建一个 API 接口，通过农历获取星盘信息
app.post("/api/astro/lunar", (req, res) => {
    const { date, timezone, gender } = req.body;

    // 检查请求参数
    if (!date  || !gender) {
        return res.status(400).json({ error: "缺少必要的参数" });
    }

    try {
        // 通过农历获取星盘信息
        const astrolabeLunar = astro.byLunar(date, timezone, gender);
        return res.json(astrolabeLunar);
    } catch (error) {
        return res.status(500).json({ error: "计算农历星盘信息时出错" });
    }
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`服务器正在运行，访问地址: http://localhost:${PORT}`);
});