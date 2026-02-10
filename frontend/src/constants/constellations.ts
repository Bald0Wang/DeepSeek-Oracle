export type ElementKey = "wood" | "fire" | "earth" | "metal" | "water";

export interface ElementMeta {
  key: ElementKey;
  label: string;
  icon: string;
}

export interface ConstellationInfo {
  nameCn: string;
  nameEn: string;
  element: ElementKey;
  summary: string;
  verse: string;
}

export const ELEMENT_METAS: Record<ElementKey, ElementMeta> = {
  wood: { key: "wood", label: "木", icon: "木" },
  fire: { key: "fire", label: "火", icon: "火" },
  earth: { key: "earth", label: "土", icon: "土" },
  metal: { key: "metal", label: "金", icon: "金" },
  water: { key: "water", label: "水", icon: "水" },
};

export const ELEMENT_SEQUENCE: ElementKey[] = ["wood", "fire", "earth", "metal", "water"];

export const CONSTELLATION_SWITCH_INTERVAL_MS = 9000;

export const CONSTELLATION_INFOS: ConstellationInfo[] = [
  {
    nameCn: "天机星轨",
    nameEn: "Tian Ji",
    element: "wood",
    summary: "主谋略与判断，强调关系中的节奏与选择时机。",
    verse: "机星动，局势明。",
  },
  {
    nameCn: "太阴星轨",
    nameEn: "Tai Yin",
    element: "water",
    summary: "主情感与内在需求，映射长期相处中的安全感与温度。",
    verse: "月光柔，情绪定。",
  },
  {
    nameCn: "紫微星轨",
    nameEn: "Zi Wei",
    element: "earth",
    summary: "主主导与格局，提示关系方向与核心责任分配。",
    verse: "紫垣定，心位安。",
  },
];
