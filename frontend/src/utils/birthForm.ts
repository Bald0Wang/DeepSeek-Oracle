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

export const toBirthInfo = (form: ZiweiFortuneFormState): BirthInfo => {
  const yearNumber = Number(form.year);
  const monthNumber = Number(form.month);
  const dayNumber = Number(form.day);
  const hourNumber = Number(form.hour);

  return {
    date: `${yearNumber}-${pad2(monthNumber)}-${pad2(dayNumber)}`,
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

