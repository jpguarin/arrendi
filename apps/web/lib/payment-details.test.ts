import assert from "node:assert/strict";
import { test } from "node:test";

import { composePaymentDetails, isWallet } from "./payment-details.ts";

const holder = { name: "Carolina Gómez", document: "C.C. 52.814.337" };

test("a bank account says the bank, its kind, its number and whose it is", () => {
  assert.equal(
    composePaymentDetails(
      { bank: "Bancolombia", otherBank: "", type: "Ahorros", number: " 123-456789-01 " },
      holder,
    ),
    "Bancolombia · Ahorros N.º 123-456789-01\nA nombre de Carolina Gómez, C.C. 52.814.337",
  );
});

test("a wallet goes by the phone, without a kind of account", () => {
  assert.equal(
    composePaymentDetails(
      { bank: "Nequi", otherBank: "", type: "Corriente", number: "300 123 4567" },
      holder,
    ),
    "Nequi al 300 123 4567\nA nombre de Carolina Gómez, C.C. 52.814.337",
  );
  assert.equal(isWallet("Daviplata"), true);
  assert.equal(isWallet("BBVA"), false);
});

test("another bank uses the name the owner wrote", () => {
  assert.equal(
    composePaymentDetails(
      { bank: "Otro", otherBank: " Banco de Occidente ", type: "Corriente", number: "99" },
      holder,
    ),
    "Banco de Occidente · Corriente N.º 99\nA nombre de Carolina Gómez, C.C. 52.814.337",
  );
  assert.equal(
    composePaymentDetails({ bank: "Otro", otherBank: "", type: "Ahorros", number: "99" }, holder),
    "Banco · Ahorros N.º 99\nA nombre de Carolina Gómez, C.C. 52.814.337",
  );
});

test("whose it is leaves out what is not known yet", () => {
  const account = { bank: "BBVA", otherBank: "", type: "Ahorros" as const, number: "1" };
  assert.equal(
    composePaymentDetails(account, { name: "Carolina Gómez", document: "" }),
    "BBVA · Ahorros N.º 1\nA nombre de Carolina Gómez",
  );
  assert.equal(composePaymentDetails(account, { name: " ", document: "" }), "BBVA · Ahorros N.º 1");
});

test("without a bank or a number there is nothing to write", () => {
  assert.equal(
    composePaymentDetails({ bank: "", otherBank: "", type: "Ahorros", number: "1" }, holder),
    "",
  );
  assert.equal(
    composePaymentDetails({ bank: "BBVA", otherBank: "", type: "Ahorros", number: "  " }, holder),
    "",
  );
});
