// How the owner gets paid, put together from taps: the bank, the kind of account and its
// number. What it writes is the same free text Ajustes keeps, and it can be edited.

export const BANKS = [
  "Bancolombia",
  "Davivienda",
  "Banco de Bogotá",
  "BBVA",
  "Banco Popular",
  "Colpatria",
  "Nequi",
  "Daviplata",
  "Otro",
] as const;

/** The banks that go by a phone number instead of an account. */
const WALLETS: readonly string[] = ["Nequi", "Daviplata"];

export const ACCOUNT_TYPES = ["Ahorros", "Corriente"] as const;
export type AccountType = (typeof ACCOUNT_TYPES)[number];

export type PaymentAccount = {
  bank: string;
  /** The bank's name when it is not on the list. */
  otherBank: string;
  type: AccountType;
  number: string;
};

export const isWallet = (bank: string) => WALLETS.includes(bank);

/**
 * The text the tenant reads after "Pagar a:", or an empty one while the bank or the
 * number is missing. `holder.document` comes written, as "C.C. 52.814.337".
 */
export function composePaymentDetails(
  account: PaymentAccount,
  holder: { name: string; document: string },
): string {
  const number = account.number.trim();
  if (!account.bank || !number) return "";
  const bank = account.bank === "Otro" ? account.otherBank.trim() || "Banco" : account.bank;
  const where = isWallet(account.bank)
    ? `${bank} al ${number}`
    : `${bank} · ${account.type} N.º ${number}`;
  const whose = [holder.name.trim(), holder.document.trim()].filter(Boolean).join(", ");
  return whose ? `${where}\nA nombre de ${whose}` : where;
}
