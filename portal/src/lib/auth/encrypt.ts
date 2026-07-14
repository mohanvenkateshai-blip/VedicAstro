/**
 * PII encryption for birth chart data at rest.
 *
 * Uses AES-256-GCM with a key derived from ENCRYPTION_KEY (env).
 * Encrypts the birth_datetime, birth_lat, birth_lon fields inside
 * chart_data before storing in the horoscopes table.
 */

import "server-only";
import {
  decryptChartDataWithKey,
  encryptChartDataWithKey,
} from "./chart-data-crypto";
import {
  decryptSavedChartDataWithKey,
  encryptSavedChartDataWithKey,
  type SavedChartSensitiveData,
} from "./saved-chart-crypto";
export {
  EncryptionConfigurationError,
  EncryptionIntegrityError,
  isEncryptedSavedChartValue,
  type SavedChartSensitiveData,
  type SavedChartSensitiveField,
} from "./saved-chart-crypto";

/** Encrypt every identifying saved-chart field using a fresh IV per field. */
export async function encryptSavedChartData(
  data: SavedChartSensitiveData,
  owner: string,
): Promise<SavedChartSensitiveData> {
  return encryptSavedChartDataWithKey(data, owner, process.env.ENCRYPTION_KEY ?? "");
}

/**
 * Decrypt an encrypted saved chart while leaving legacy plaintext columns
 * untouched. This mixed-read path permits a deployment-safe rolling migration.
 * Encrypted values never fall back to ciphertext or plaintext on key failure.
 */
export async function decryptSavedChartData(
  data: SavedChartSensitiveData,
  owner: string,
): Promise<SavedChartSensitiveData> {
  return decryptSavedChartDataWithKey(data, owner, process.env.ENCRYPTION_KEY ?? "");
}

/**
 * Encrypt the birth-sensitive fields in chart_data.
 * Replaces birth_datetime, birth_lat, birth_lon in meta with their
 * encrypted hex representations. Non-destructive — the original chart
 * positions/planets remain readable.
 */
export async function encryptChartData(chartData: Record<string, unknown>): Promise<Record<string, unknown>> {
  return encryptChartDataWithKey(chartData, process.env.ENCRYPTION_KEY ?? "");
}

/**
 * Decrypt chart data for display. Returns original plaintext.
 */
export async function decryptChartData(chartData: Record<string, unknown>): Promise<Record<string, unknown>> {
  return decryptChartDataWithKey(chartData, process.env.ENCRYPTION_KEY ?? "");
}
