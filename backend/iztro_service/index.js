const express = require("express");
const { astro } = require("iztro");

const app = express();
const PORT = 3000;

app.use(express.json());

app.post("/api/astro/solar", (req, res) => {
  const { date, timezone, gender } = req.body;
  if (!date || !gender) {
    return res.status(400).json({ error: "missing required parameters" });
  }

  try {
    const astrolabeSolar = astro.bySolar(date, timezone, gender);
    return res.json(astrolabeSolar);
  } catch (error) {
    return res.status(500).json({ error: "failed to generate solar chart" });
  }
});

app.post("/api/astro/lunar", (req, res) => {
  const { date, timezone, gender } = req.body;
  if (!date || !gender) {
    return res.status(400).json({ error: "missing required parameters" });
  }

  try {
    const astrolabeLunar = astro.byLunar(date, timezone, gender);
    return res.json(astrolabeLunar);
  } catch (error) {
    return res.status(500).json({ error: "failed to generate lunar chart" });
  }
});

app.listen(PORT, () => {
  console.log(`iztro service is running on http://localhost:${PORT}`);
});
