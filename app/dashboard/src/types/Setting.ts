export type SettingValue = string | number | boolean | null | SettingValue[] | { [key: string]: SettingValue };

export type Setting = {
  key: string;
  value: SettingValue;
  updated_at: string;
};
