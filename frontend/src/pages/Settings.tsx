import { FormEvent, useEffect, useMemo, useState } from "react";

import { getLLMSettings, updateLLMSettings } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import type { LLMMode, LLMProvider, LLMProviderOption } from "../types";

const PROVIDERS: LLMProvider[] = ["glm", "volcano", "deepseek", "qwen", "aliyun"];

const normalizeProvider = (value: string, fallback: LLMProvider): LLMProvider => {
  if (PROVIDERS.includes(value as LLMProvider)) {
    return value as LLMProvider;
  }
  return fallback;
};

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [mode, setMode] = useState<LLMMode>("system");
  const [provider, setProvider] = useState<LLMProvider>("glm");
  const [model, setModel] = useState("glm-5");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [hasStoredApiKey, setHasStoredApiKey] = useState(false);
  const [providerOptions, setProviderOptions] = useState<LLMProviderOption[]>([]);
  const [defaults, setDefaults] = useState<{ provider: LLMProvider; model: string }>({
    provider: "glm",
    model: "glm-5",
  });

  const selectedOption = useMemo(
    () => providerOptions.find((item) => item.provider === provider) || null,
    [provider, providerOptions]
  );

  const modelChoices = selectedOption?.system_models || [];

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getLLMSettings();
        const data = res.data;
        if (!data) {
          throw new Error("获取设置失败");
        }
        const defaultProvider = normalizeProvider(data.defaults.provider, "glm");
        const settingProvider = normalizeProvider(data.setting.provider, defaultProvider);
        if (cancelled) {
          return;
        }

        setDefaults({ provider: defaultProvider, model: data.defaults.model || "glm-5" });
        setProviderOptions(Array.isArray(data.provider_options) ? data.provider_options : []);
        setMode(data.setting.mode);
        setProvider(settingProvider);
        setModel(data.setting.model || data.defaults.model || "glm-5");
        setBaseUrl(data.setting.base_url || "");
        setHasStoredApiKey(Boolean(data.setting.has_api_key));
      } catch (err) {
        if (cancelled) {
          return;
        }
        const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
        setError(apiMessage || (err instanceof Error ? err.message : "加载设置失败，请稍后重试。"));
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  const applySystemDefault = () => {
    setMode("system");
    setProvider(defaults.provider);
    setModel(defaults.model);
    setApiKey("");
    setBaseUrl("");
  };

  const onProviderChange = (value: string) => {
    const nextProvider = normalizeProvider(value, defaults.provider);
    setProvider(nextProvider);
    const nextOption = providerOptions.find((item) => item.provider === nextProvider);
    if (nextOption && nextOption.system_models.length > 0 && !nextOption.system_models.includes(model)) {
      setModel(nextOption.system_models[0]);
    }
    if (!nextOption?.supports_base_url) {
      setBaseUrl("");
    }
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const normalizedModel = model.trim();
    if (!normalizedModel) {
      setError("请填写模型名称。");
      return;
    }

    const payload = {
      mode,
      provider,
      model: normalizedModel,
      ...(mode === "custom" && apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      ...(mode === "custom" && selectedOption?.supports_base_url ? { base_url: baseUrl.trim() } : {}),
    };

    setSaving(true);
    try {
      const res = await updateLLMSettings(payload);
      if (!res.data?.setting) {
        throw new Error("保存失败");
      }
      const setting = res.data.setting;
      setMode(setting.mode);
      setProvider(normalizeProvider(setting.provider, defaults.provider));
      setModel(setting.model);
      setBaseUrl(setting.base_url || "");
      setHasStoredApiKey(Boolean(setting.has_api_key));
      setApiKey("");
      setMessage("模型配置已保存，下次请求自动生效。\n正在进行中的任务将继续使用提交时配置。");
    } catch (err) {
      const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(apiMessage || (err instanceof Error ? err.message : "保存失败，请稍后重试。"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page fade-in">
      <InkCard title="模型设置" icon="模" className="settings-card">
        {loading ? <p className="loading-state-text">正在加载模型配置...</p> : null}

        {!loading ? (
          <form className="stack" onSubmit={onSubmit}>
            <div className="settings-mode-toggle" role="tablist" aria-label="模型模式">
              <button
                type="button"
                className={mode === "system" ? "settings-mode-toggle__btn settings-mode-toggle__btn--active" : "settings-mode-toggle__btn"}
                onClick={applySystemDefault}
              >
                系统内置
              </button>
              <button
                type="button"
                className={mode === "custom" ? "settings-mode-toggle__btn settings-mode-toggle__btn--active" : "settings-mode-toggle__btn"}
                onClick={() => setMode("custom")}
              >
                自定义模型
              </button>
            </div>

            <p className="field__hint">
              系统内置：使用平台统一配置。自定义模型：保存你的 provider/model/key 到账号，后续自动复用。
            </p>

            <div className="field">
              <label className="field__label" htmlFor="settings-provider">模型提供方</label>
              <select
                id="settings-provider"
                value={provider}
                onChange={(event) => onProviderChange(event.target.value)}
              >
                {providerOptions.map((item) => (
                  <option key={item.provider} value={item.provider}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label className="field__label" htmlFor="settings-model">模型名称</label>
              <input
                id="settings-model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder="例如 glm-5"
                list="settings-model-options"
              />
              <datalist id="settings-model-options">
                {modelChoices.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
              {modelChoices.length > 0 ? (
                <div className="settings-model-chips">
                  {modelChoices.map((item) => (
                    <button
                      key={item}
                      type="button"
                      className={item === model ? "settings-model-chip settings-model-chip--active" : "settings-model-chip"}
                      onClick={() => setModel(item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            {mode === "custom" ? (
              <>
                <div className="field">
                  <label className="field__label" htmlFor="settings-apikey">API Key</label>
                  <input
                    id="settings-apikey"
                    type="password"
                    autoComplete="new-password"
                    value={apiKey}
                    onChange={(event) => setApiKey(event.target.value)}
                    placeholder={hasStoredApiKey ? "已保存，留空则保持不变" : "请输入你的 API Key"}
                  />
                  {hasStoredApiKey ? <p className="field__hint">已存在密钥，留空将继续使用当前密钥。</p> : null}
                </div>

                {selectedOption?.supports_base_url ? (
                  <div className="field">
                    <label className="field__label" htmlFor="settings-base-url">Base URL（可选）</label>
                    <input
                      id="settings-base-url"
                      value={baseUrl}
                      onChange={(event) => setBaseUrl(event.target.value)}
                      placeholder="https://example.com/v1"
                    />
                  </div>
                ) : null}
              </>
            ) : null}

            {error ? <p className="error-text">{error}</p> : null}
            {message ? <p className="success-text">{message}</p> : null}

            <div className="actions-row">
              <InkButton type="submit" disabled={saving}>
                {saving ? "保存中..." : "保存设置"}
              </InkButton>
            </div>
          </form>
        ) : null}
      </InkCard>
    </div>
  );
}
