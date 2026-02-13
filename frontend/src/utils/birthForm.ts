import type { ZiweiFortuneFormState } from "../stores/ziweiFortuneSession";
import type { BirthInfo } from "../types";

const pad2 = (value: number) => String(value).padStart(2, "0");

const hourToTimezone = (hour: number) => {
  if (hour === 23) {
    return 12;
  }
  if (hour === 0) {
    return 0;
  }
  return Math.floor((hour + 1) / 2);
};

interface TrueSolarCityOption {
  code: string;
  name: string;
  longitude: number;
}

interface TrueSolarProvinceOption {
  code: string;
  name: string;
  cities: TrueSolarCityOption[];
}

interface TrueSolarCorrectionResult {
  cityName: string;
  longitude: number;
  longitudeOffsetMinutes: number;
  equationOfTimeMinutes: number;
  totalOffsetMinutes: number;
  correctedDate: string;
  correctedHour: number;
  correctedMinute: number;
}

/**
 * 中国34个省级行政区（按省会/代表城市）经度数据，用于真太阳时修正。
 */
export const TRUE_SOLAR_PROVINCES: TrueSolarProvinceOption[] = [
  { code: "beijing", name: "北京", cities: [{ code: "beijing", name: "北京", longitude: 116.41 }] },
  { code: "tianjin", name: "天津", cities: [{ code: "tianjin", name: "天津", longitude: 117.2 }] },
  { code: "shanghai", name: "上海", cities: [{ code: "shanghai", name: "上海", longitude: 121.47 }] },
  { code: "chongqing", name: "重庆", cities: [{ code: "chongqing", name: "重庆", longitude: 106.55 }] },
  { code: "hebei", name: "河北", cities: [{ code: "shijiazhuang", name: "石家庄", longitude: 114.51 }] },
  { code: "shanxi", name: "山西", cities: [{ code: "taiyuan", name: "太原", longitude: 112.55 }] },
  { code: "liaoning", name: "辽宁", cities: [{ code: "shenyang", name: "沈阳", longitude: 123.43 }] },
  { code: "jilin", name: "吉林", cities: [{ code: "changchun", name: "长春", longitude: 125.32 }] },
  { code: "heilongjiang", name: "黑龙江", cities: [{ code: "haerbin", name: "哈尔滨", longitude: 126.64 }] },
  { code: "jiangsu", name: "江苏", cities: [{ code: "nanjing", name: "南京", longitude: 118.8 }] },
  { code: "zhejiang", name: "浙江", cities: [{ code: "hangzhou", name: "杭州", longitude: 120.16 }] },
  { code: "anhui", name: "安徽", cities: [{ code: "hefei", name: "合肥", longitude: 117.23 }] },
  { code: "fujian", name: "福建", cities: [{ code: "fuzhou", name: "福州", longitude: 119.3 }] },
  { code: "jiangxi", name: "江西", cities: [{ code: "nanchang", name: "南昌", longitude: 115.86 }] },
  { code: "shandong", name: "山东", cities: [{ code: "jinan", name: "济南", longitude: 117.12 }] },
  { code: "henan", name: "河南", cities: [{ code: "zhengzhou", name: "郑州", longitude: 113.63 }] },
  { code: "hubei", name: "湖北", cities: [{ code: "wuhan", name: "武汉", longitude: 114.31 }] },
  { code: "hunan", name: "湖南", cities: [{ code: "changsha", name: "长沙", longitude: 112.94 }] },
  { code: "guangdong", name: "广东", cities: [{ code: "guangzhou", name: "广州", longitude: 113.26 }] },
  { code: "hainan", name: "海南", cities: [{ code: "haikou", name: "海口", longitude: 110.33 }] },
  { code: "sichuan", name: "四川", cities: [{ code: "chengdu", name: "成都", longitude: 104.07 }] },
  { code: "guizhou", name: "贵州", cities: [{ code: "guiyang", name: "贵阳", longitude: 106.63 }] },
  { code: "yunnan", name: "云南", cities: [{ code: "kunming", name: "昆明", longitude: 102.83 }] },
  { code: "shanxi2", name: "陕西", cities: [{ code: "xian", name: "西安", longitude: 108.94 }] },
  { code: "gansu", name: "甘肃", cities: [{ code: "lanzhou", name: "兰州", longitude: 103.83 }] },
  { code: "qinghai", name: "青海", cities: [{ code: "xining", name: "西宁", longitude: 101.78 }] },
  { code: "taiwan", name: "台湾", cities: [{ code: "taipei", name: "台北", longitude: 121.57 }] },
  { code: "neimenggu", name: "内蒙古", cities: [{ code: "huhehaote", name: "呼和浩特", longitude: 111.67 }] },
  { code: "guangxi", name: "广西", cities: [{ code: "nanning", name: "南宁", longitude: 108.37 }] },
  { code: "xizang", name: "西藏", cities: [{ code: "lasa", name: "拉萨", longitude: 91.13 }] },
  { code: "ningxia", name: "宁夏", cities: [{ code: "yinchuan", name: "银川", longitude: 106.28 }] },
  { code: "xinjiang", name: "新疆", cities: [{ code: "wulumuqi", name: "乌鲁木齐", longitude: 87.62 }] },
  { code: "hongkong", name: "香港", cities: [{ code: "hongkong", name: "香港", longitude: 114.17 }] },
  { code: "macao", name: "澳门", cities: [{ code: "macao", name: "澳门", longitude: 113.54 }] },
];

/**
 * 提供省份下拉选项列表。
 */
export const getTrueSolarProvinceOptions = () =>
  TRUE_SOLAR_PROVINCES.map((item) => ({ code: item.code, name: item.name }));

/**
 * 根据省份编码获取城市选项列表。
 */
export const getTrueSolarCityOptions = (provinceCode: string) => {
  const province = TRUE_SOLAR_PROVINCES.find((item) => item.code === provinceCode) || TRUE_SOLAR_PROVINCES[0];
  return (province?.cities || []).map((city) => ({ code: city.code, name: city.name, longitude: city.longitude }));
};

/**
 * 计算指定日期在一年中的序号（1-366）。
 */
const dayOfYear = (year: number, month: number, day: number) => {
  const current = Date.UTC(year, month - 1, day);
  const start = Date.UTC(year, 0, 0);
  return Math.floor((current - start) / 86400000);
};

/**
 * 计算均时差（Equation of Time, 分钟），采用常见近似公式。
 */
const equationOfTimeMinutes = (year: number, month: number, day: number) => {
  const n = dayOfYear(year, month, day);
  const b = (2 * Math.PI * (n - 81)) / 364;
  return 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
};

/**
 * 根据省市经度和均时差，计算真太阳时校正后的日期与时分。
 */
const computeTrueSolarCorrection = (form: ZiweiFortuneFormState): TrueSolarCorrectionResult => {
  const province = TRUE_SOLAR_PROVINCES.find((item) => item.code === form.provinceCode) || TRUE_SOLAR_PROVINCES[0];
  const city = (province?.cities || []).find((item) => item.code === form.cityCode) || (province?.cities || [])[0];

  const year = Number(form.year);
  const month = Number(form.month);
  const day = Number(form.day);
  const hour = Number(form.hour);
  const minute = Number(form.minute);
  const longitude = city?.longitude ?? 116.41;

  const eot = equationOfTimeMinutes(year, month, day);
  const longitudeOffset = 4 * (longitude - 120);
  const totalOffset = longitudeOffset + eot;
  const offsetRounded = Math.round(totalOffset);

  const rawTs = Date.UTC(year, month - 1, day, hour, minute, 0);
  const correctedTs = rawTs + offsetRounded * 60_000;
  const corrected = new Date(correctedTs);

  const correctedYear = corrected.getUTCFullYear();
  const correctedMonth = corrected.getUTCMonth() + 1;
  const correctedDay = corrected.getUTCDate();
  const correctedHour = corrected.getUTCHours();
  const correctedMinute = corrected.getUTCMinutes();

  return {
    cityName: city?.name || "北京",
    longitude,
    longitudeOffsetMinutes: longitudeOffset,
    equationOfTimeMinutes: eot,
    totalOffsetMinutes: totalOffset,
    correctedDate: `${correctedYear}-${pad2(correctedMonth)}-${pad2(correctedDay)}`,
    correctedHour,
    correctedMinute,
  };
};

export const validateBirthForm = (form: ZiweiFortuneFormState): string | null => {
  const yearNumber = Number(form.year);
  const monthNumber = Number(form.month);
  const dayNumber = Number(form.day);
  const hourNumber = Number(form.hour);
  const minuteNumber = Number(form.minute);

  if ([yearNumber, monthNumber, dayNumber, hourNumber, minuteNumber].some((value) => Number.isNaN(value))) {
    return "请完整填写出生年月日和时间。";
  }
  if (yearNumber < 1900 || yearNumber > 2100) {
    return "年份范围建议在 1900-2100。";
  }
  if (monthNumber < 1 || monthNumber > 12) {
    return "月份范围应为 1-12。";
  }

  if (form.calendar === "lunar") {
    if (dayNumber < 1 || dayNumber > 30) {
      return "阴历日期范围应为 1-30。";
    }
  } else {
    const temp = new Date(yearNumber, monthNumber - 1, dayNumber);
    const isValidSolarDate =
      temp.getFullYear() === yearNumber
      && temp.getMonth() === monthNumber - 1
      && temp.getDate() === dayNumber;
    if (!isValidSolarDate) {
      return "阳历日期无效，请检查年月日。";
    }
  }

  if (hourNumber < 0 || hourNumber > 23 || minuteNumber < 0 || minuteNumber > 59) {
    return "时间无效，请使用 24 小时制。";
  }

  return null;
};

/**
 * 生成真太阳时修正说明文本，用于页面提示。
 */
export const formatTrueSolarCorrectionPreview = (form: ZiweiFortuneFormState): string => {
  if (!form.enableTrueSolar) {
    return "真太阳时校正未启用。";
  }
  const correction = computeTrueSolarCorrection(form);
  const sign = correction.totalOffsetMinutes >= 0 ? "+" : "";
  return [
    `按 ${correction.cityName} 经度 ${correction.longitude.toFixed(2)}° 进行校正`,
    `经度修正 ${correction.longitudeOffsetMinutes.toFixed(1)} 分钟，均时差 ${correction.equationOfTimeMinutes.toFixed(1)} 分钟`,
    `总修正 ${sign}${correction.totalOffsetMinutes.toFixed(1)} 分钟，校正后时间 ${correction.correctedDate} ${pad2(correction.correctedHour)}:${pad2(correction.correctedMinute)}`,
  ].join("；");
};

export const toBirthInfo = (form: ZiweiFortuneFormState): BirthInfo => {
  const yearNumber = Number(form.year);
  const monthNumber = Number(form.month);
  const dayNumber = Number(form.day);
  let dateText = `${yearNumber}-${pad2(monthNumber)}-${pad2(dayNumber)}`;
  let hourNumber = Number(form.hour);

  if (form.enableTrueSolar) {
    const correction = computeTrueSolarCorrection(form);
    dateText = correction.correctedDate;
    hourNumber = correction.correctedHour;
  }

  return {
    date: dateText,
    timezone: hourToTimezone(hourNumber),
    gender: form.gender,
    calendar: form.calendar,
  };
};

export const formatBirthPreview = (form: ZiweiFortuneFormState): string => {
  const y = Number(form.year) || 0;
  const m = Number(form.month) || 0;
  const d = Number(form.day) || 0;
  const h = Number(form.hour) || 0;
  const min = Number(form.minute) || 0;
  return `${form.calendar === "lunar" ? "阴历" : "阳历"} ${y}年${m}月${d}日 ${pad2(h)}:${pad2(min)} ${form.gender}`;
};

