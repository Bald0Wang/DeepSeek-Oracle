export interface HomeVariantSpec {
  id: string;
  name: string;
  tagline: string;
  mood: string;
  className: string;
}

export const HOME_VARIANTS: HomeVariantSpec[] = [
  {
    id: "celestial-bronze",
    name: "星盘青铜",
    tagline: "古典命理 + 星图叙事",
    mood: "厚重、神秘、仪式感",
    className: "variant-celestial-bronze",
  },
  {
    id: "ink-minimal",
    name: "水墨极简",
    tagline: "留白、墨色、轻信息密度",
    mood: "克制、宁静、专业",
    className: "variant-ink-minimal",
  },
  {
    id: "ink-vermilion",
    name: "朱印留白",
    tagline: "中国红 + 宣纸白 + 印章点缀",
    mood: "典雅、节制、东方感",
    className: "variant-ink-vermilion",
  },
  {
    id: "sunrise-paper",
    name: "曦纸晨光",
    tagline: "暖色纸感与浅浮雕",
    mood: "温和、安心、亲近",
    className: "variant-sunrise-paper",
  },
  {
    id: "ocean-mystic",
    name: "深海秘仪",
    tagline: "蓝金对比 + 星象波纹",
    mood: "深邃、理性、探索",
    className: "variant-ocean-mystic",
  },
  {
    id: "forest-zen",
    name: "林岚禅意",
    tagline: "低饱和自然系 + 呼吸感布局",
    mood: "治愈、沉稳、松弛",
    className: "variant-forest-zen",
  },
  {
    id: "neon-future",
    name: "霓虹未来",
    tagline: "高对比 HUD 风格",
    mood: "锐利、年轻、实验",
    className: "variant-neon-future",
  },
  {
    id: "art-deco",
    name: "摩登装饰",
    tagline: "几何线条 + 复古华饰",
    mood: "华丽、秩序、纪念性",
    className: "variant-art-deco",
  },
  {
    id: "clay-organic",
    name: "陶土有机",
    tagline: "柔边块面 + 手作质感",
    mood: "温润、自然、生活化",
    className: "variant-clay-organic",
  },
  {
    id: "noir-gold",
    name: "夜幕鎏金",
    tagline: "黑金高反差 + 纵深阴影",
    mood: "尊贵、果断、强表达",
    className: "variant-noir-gold",
  },
  {
    id: "aurora-glass",
    name: "极光玻璃",
    tagline: "半透明层叠 + 极光光带",
    mood: "轻盈、现代、灵动",
    className: "variant-aurora-glass",
  },
];

export const DEFAULT_HOME_VARIANT_ID = HOME_VARIANTS[0].id;
