# Baseline inventory and static dependency evidence

Baseline `16085f825fef25ee4112d74b729c57e623b0bb05`; default `main`; audit branch `docs/planning-audit-20261110`.

- Tracked baseline files inventoried: **379**.
- Backend Python files parsed with Python AST: **225**, syntax parse failures **0**.
- Actual domain directories: **15**.
- Directed cross-domain edges excluding migrations, including management: **57**; excluding management: **50**.

Inventory establishes file existence/object identity; AST parsing establishes syntax/import-declaration evidence only. Neither establishes runtime behavior, executed tests or manual line-by-line review of every file. Manual inspection scope is identified in the four specialist reports and main report. Files added by this audit are not part of this baseline inventory.

Source scan includes deferred `domains.*` imports and composition hooks, excludes migrations from dependency edges and labels management/seed callers. Relative imports, dynamic strings and non-Python runtime dependencies require manual interpretation. No application imports or application code execution performed.

## Baseline tracked-file manifest

| Path | Git blob SHA | Bytes | Inventory method |
|---|---|---:|---|
| `.github/workflows/ci.yml` | `f498affda6d401d8b95fc59c1271c5a11aeff48a` | 3345 | file inventory |
| `.gitignore` | `983be01aa7a5c77825b020227ac0ba9559fa4c8c` | 403 | file inventory |
| `CONTRACT.md` | `071695dec9b16cd2abae7644ced7794ff1e78f2e` | 13406 | file inventory |
| `Makefile` | `2e47b9f0e5c871e2a284ad3aac334490b1a3ada1` | 2959 | file inventory |
| `README.md` | `a73179d755a64a2ce00376e860f5ed85e4e29769` | 3291 | file inventory |
| `apps/web/.eslintrc.cjs` | `02fc71263ca15fe220382dadf2b709bfd18c6061` | 704 | file inventory |
| `apps/web/.gitignore` | `6258f2b566f21260d3f48ea496923d34a698f802` | 146 | file inventory |
| `apps/web/e2e/helpers/harness.ts` | `7ddb93e6d5a01b1947be4cf84c7a051cbeacaa1f` | 2200 | file inventory |
| `apps/web/e2e/playwright.config.ts` | `d63cd263077f048f8b8f5f529141d8bd048fcbfe` | 1445 | file inventory |
| `apps/web/e2e/run.sh` | `106f2bc45a3beb7fbf54de2fe353642a3cbad15d` | 4607 | file inventory |
| `apps/web/e2e/serve.sh` | `b851731163a95749f9314f165a3dda29f7f87e71` | 358 | file inventory |
| `apps/web/e2e/specs/auth.spec.ts` | `7e8ff0534505b74124160fb616a70c6e855942fb` | 3891 | file inventory |
| `apps/web/e2e/specs/billing.spec.ts` | `5795fb17b9a5d79c6dfcdfbd3e19f441e1d78c7a` | 7223 | file inventory |
| `apps/web/e2e/specs/nav.spec.ts` | `c2d5a745075b082c6b0dd5bbe681bd82c1a8e555` | 1110 | file inventory |
| `apps/web/e2e/specs/routers.spec.ts` | `8587694ec0d264e53ded384f948e95292f58a3a1` | 5578 | file inventory |
| `apps/web/index.html` | `da4763110eb02d4a34383ae6c363e5c7b3e8542a` | 344 | file inventory |
| `apps/web/package.json` | `773fc95698707b9d60324bf52e2ceba868307d67` | 1476 | file inventory |
| `apps/web/pnpm-lock.yaml` | `2cd76459991a67400cb0268f2ccba55b5f8777bc` | 108447 | file inventory |
| `apps/web/pnpm-workspace.yaml` | `5ed0b5af0d45919f64c66edfb16a5f4512461fa1` | 29 | file inventory |
| `apps/web/scripts/build_catalogs.py` | `212f92b9086ffab76393c421733ae287ad3ca1d9` | 84477 | file inventory |
| `apps/web/scripts/check_contrast.py` | `9af459666188ee8d4f481dbd507c03ccbee73932` | 2420 | file inventory |
| `apps/web/scripts/check_i18n.py` | `1c05d18c8ba69756406b5122c964cf8a091c09ab` | 7917 | file inventory |
| `apps/web/scripts/visual_sweep.sh` | `05d51b583a3f9076c4bda65d87e6010600ea3a71` | 1743 | file inventory |
| `apps/web/src/api/api.test.tsx` | `9d852a1257f78c64054500e1bbd1317d33f73b32` | 5261 | file inventory |
| `apps/web/src/api/billing-adapter.test.tsx` | `b7761a19cd658261b18416892930755fd0d7bd16` | 5227 | file inventory |
| `apps/web/src/api/client.ts` | `4181fecbc74651e6f2f5497e4f06ce349109851f` | 12582 | file inventory |
| `apps/web/src/api/contracts.ts` | `aa649dcf4c20d4527fff893785936d10392c9f00` | 14052 | file inventory |
| `apps/web/src/api/http.ts` | `01525b318adb453926d92f2a264e2d46329941e7` | 4037 | file inventory |
| `apps/web/src/api/index.tsx` | `ff11672141752ac2379e422cab46826def152c47` | 1483 | file inventory |
| `apps/web/src/api/live/adapter.ts` | `aba5f586f5a9e41813c54d6c95d6e5dc4f25d415` | 16410 | file inventory |
| `apps/web/src/api/mock/adapter.ts` | `b561eb13c322a69846ae562c40dbebf415a5c496` | 53638 | file inventory |
| `apps/web/src/api/mock/fixtures.ts` | `8fc8d3c2ef535fc26b685c9dd67b0ef480d5762d` | 25013 | file inventory |
| `apps/web/src/app/App.tsx` | `d78cadb4126ffb1efd0a1d49b719508fc37e5ed8` | 8597 | file inventory |
| `apps/web/src/branding/index.tsx` | `b4750c1ea9886d34076059221d6916a9324e8357` | 1401 | file inventory |
| `apps/web/src/design-system/components/AppShell.tsx` | `b21c27e5dedb58d657a2ebb938480ac193e72482` | 15691 | file inventory |
| `apps/web/src/design-system/components/ChartWithTable.tsx` | `9a4186c4a5bbe82e4bcccf6a8386d60c715fab5e` | 4655 | file inventory |
| `apps/web/src/design-system/components/DataParts.tsx` | `67f7bc41ab18c79d46dd7558cd4c42ffd1182ff3` | 5944 | file inventory |
| `apps/web/src/design-system/components/DataTable.tsx` | `2ce7f2234813f4b45e9b77de6ecb89e6159a9aba` | 5470 | file inventory |
| `apps/web/src/design-system/components/JobProgress.tsx` | `2a3dc60efbfb40f6d4dd395754461e2a46242180` | 2977 | file inventory |
| `apps/web/src/design-system/components/MetricCard.tsx` | `db55f4531e6c7ebb1634bea7145a1e5256e525de` | 1884 | file inventory |
| `apps/web/src/design-system/components/Notices.tsx` | `70172d10ff5c5f737fd86c961e8778bd52ad1947` | 2654 | file inventory |
| `apps/web/src/design-system/components/PageHeader.tsx` | `dee446911df4b70d06be7439a278fd4a581fbb6e` | 1308 | file inventory |
| `apps/web/src/design-system/components/StatusBadge.tsx` | `420089268f86c190b3d8e8944acae33a22a92be3` | 2500 | file inventory |
| `apps/web/src/design-system/components/components.css` | `16a57779afa70713f1182459e0782ad53ca70eb6` | 11906 | file inventory |
| `apps/web/src/design-system/primitives/Button.tsx` | `8d3b37afc4264791dc09219dc6c2b551becbeb79` | 2369 | file inventory |
| `apps/web/src/design-system/primitives/Dialog.tsx` | `ebfa7016eac954e1721ca3c406581e6d044d1eda` | 4728 | file inventory |
| `apps/web/src/design-system/primitives/Icon.tsx` | `b7aab8d83764c58f3967dea9ed6e868a181238db` | 5647 | file inventory |
| `apps/web/src/design-system/primitives/Input.tsx` | `4f7f5a8f80d6a9ad2eaba61b692feed58507aa09` | 5229 | file inventory |
| `apps/web/src/design-system/primitives/Misc.tsx` | `23674164546b2568b35a09544189615e16162a75` | 5518 | file inventory |
| `apps/web/src/design-system/primitives/Toast.tsx` | `1bfaf4caad43805ecb8d48783eec0d5eb8d297ba` | 2197 | file inventory |
| `apps/web/src/design-system/primitives/primitives.css` | `2633c4480811516b9ebaef4384df17c23f894361` | 15741 | file inventory |
| `apps/web/src/features/activation/ActivationPage.tsx` | `60bf406d17b61943df6e6a99914f17b274a47eb9` | 14927 | file inventory |
| `apps/web/src/features/admin/AdminSubscriptionsPage.tsx` | `c98dc81764635c314b357027cb69eabe3711a8a3` | 9727 | file inventory |
| `apps/web/src/features/auth/LoginPage.tsx` | `1375d348f2dc1143d7bba0b4e36189f3928f32a9` | 6284 | file inventory |
| `apps/web/src/features/auth/RecoverPage.tsx` | `c035fc9f4275da4b7c5b9ac469865c2aca60cc08` | 2578 | file inventory |
| `apps/web/src/features/auth/RegisterPage.tsx` | `4bbfff3a4b01ca3bfccf2855774a1dd19870d5d1` | 7149 | file inventory |
| `apps/web/src/features/auth/VerifyPage.tsx` | `34c3fee29bee61b126419bba2933f2ad35f92baa` | 2608 | file inventory |
| `apps/web/src/features/backups/BackupsPage.tsx` | `575cfb6525938493bc7070b23c20488ec439a4b2` | 9922 | file inventory |
| `apps/web/src/features/billing/BillingPage.test.tsx` | `d9a3e12c1a01cd2dd14e5d4877299ff5766a66ea` | 6831 | file inventory |
| `apps/web/src/features/billing/BillingPage.tsx` | `5f7cfbcdfe473ea0c8512c1e3fc1714f1846b1a3` | 34126 | file inventory |
| `apps/web/src/features/customers/AddCustomerDialog.tsx` | `5a0a49d938c85010dc1ab079315c235ce874624e` | 8814 | file inventory |
| `apps/web/src/features/customers/CustomerDetailPage.tsx` | `91e3a067c697a9e726e65d538b5ba3ffc7755f30` | 18814 | file inventory |
| `apps/web/src/features/customers/CustomersPage.tsx` | `286fe55b0839313c87586539941b690a832e4902` | 11076 | file inventory |
| `apps/web/src/features/imports/ImportCsvPage.tsx` | `2fb636d0f1b44f744470192cb1259c182db706d3` | 11302 | file inventory |
| `apps/web/src/features/imports/ImportRouterPage.tsx` | `54cbfa7110282957936abd2d7764c954a5bde131` | 21621 | file inventory |
| `apps/web/src/features/jobs/JobDetailPage.tsx` | `9e367c07831e1cc17722075496fa29f0e202e3d5` | 7107 | file inventory |
| `apps/web/src/features/jobs/JobsPage.tsx` | `a123b38da24a7139662e853fb98dc3a5351fef8d` | 4068 | file inventory |
| `apps/web/src/features/landing/Landing.tsx` | `04b09e0b3162af575090e592ffd649ae579f1738` | 6923 | file inventory |
| `apps/web/src/features/landing/landing.css` | `53b347f58aa72bca5a2d2fe43bb089a34958cfc7` | 3876 | file inventory |
| `apps/web/src/features/monitoring/MonitoringPage.tsx` | `eeb0fa253370d1bde35f9d0d5554c00c950e6f7b` | 8731 | file inventory |
| `apps/web/src/features/overview/OverviewPage.tsx` | `b9aa153b9a8d437cf7e540deefc1dfb8ea222cfe` | 15796 | file inventory |
| `apps/web/src/features/radius/RadiusPage.tsx` | `06169fdcb90bb127a51a90e0dddb1d004ff5fc89` | 13868 | file inventory |
| `apps/web/src/features/routers/RouterDetailPage.tsx` | `26e4f14bf4454e8f4936ed39bb6432656cb87cfe` | 18361 | file inventory |
| `apps/web/src/features/routers/RouterNewPage.test.tsx` | `e7a4607c51fcbea099cbb6cae6c8c835fd1749c7` | 4885 | file inventory |
| `apps/web/src/features/routers/RouterNewPage.tsx` | `4d9b6d30cf43ff0d3cb34a922f97368cde74f42a` | 19158 | file inventory |
| `apps/web/src/features/routers/RoutersListPage.tsx` | `3c621cfd19f3f4ebabb432e114feb65b87f0f7a5` | 5062 | file inventory |
| `apps/web/src/features/settings/PackagesPage.tsx` | `d8d724e4638c9ecd92d03e052a417a692cd8b941` | 3580 | file inventory |
| `apps/web/src/features/settings/SettingsPage.tsx` | `0ece23fbdf65dca52a553a344ad164126023bcd2` | 4180 | file inventory |
| `apps/web/src/features/settings/SubscriptionPanel.tsx` | `5a0d57355fe347eb697ddaa6eb124ad2cfceb838` | 8250 | file inventory |
| `apps/web/src/features/settings/TeamPanel.tsx` | `639cb16e4bf9a8cf36f3b2d43949ab591bdc22cc` | 3715 | file inventory |
| `apps/web/src/i18n/index.tsx` | `3b2413b5cff87bac15df4107df2ada9dbef04bb6` | 2756 | file inventory |
| `apps/web/src/i18n/useT.ts` | `7403cd1161ed03ce147ec502ee84aff3fbc4b447` | 1984 | file inventory |
| `apps/web/src/lib/billing-eligibility.test.ts` | `d6e7534b6ace360754c0cd7c7c5c67ce34e6e334` | 4072 | file inventory |
| `apps/web/src/lib/billing-eligibility.ts` | `74b8e48a960b1cef2bcfa88d9f7a21a8d75d8635` | 3894 | file inventory |
| `apps/web/src/lib/format.test.ts` | `4b172b4b3d2cfddd5369434fe789dfac38d49832` | 2149 | file inventory |
| `apps/web/src/lib/format.ts` | `0ff160ff03b357441742b220280c4d8b7cf0be44` | 5110 | file inventory |
| `apps/web/src/lib/statuses.test.ts` | `9b518be7e7a6769cb177035b3383088ea9b903ac` | 2482 | file inventory |
| `apps/web/src/lib/statuses.ts` | `94e95f220a2b194190780a6396c5938ddd52e6a1` | 5031 | file inventory |
| `apps/web/src/main.tsx` | `75735c9f84e59f2aaff349c791ee9f5208fce3f8` | 992 | file inventory |
| `apps/web/src/permissions/permissions.test.ts` | `ae81d102ca40b8832b00226c5b8272f9e70c70e4` | 2088 | file inventory |
| `apps/web/src/permissions/permissions.ts` | `b04f962076c04bae3c7fa1598e9a1ff126324677` | 3344 | file inventory |
| `apps/web/src/permissions/release-flags.test.ts` | `65ba026e115ad883e2aa5c12cba1e88a02e5cdad` | 2123 | file inventory |
| `apps/web/src/permissions/release-flags.ts` | `b4beaffb9ef268811fd4efc5d45b57d1eb31ca22` | 847 | file inventory |
| `apps/web/src/state/session.tsx` | `e812211fd1d430dfe0765e91d5ba776e95dd2940` | 3801 | file inventory |
| `apps/web/src/styles/base.css` | `f13f51d224ca3a3ca9fd86a210e03a0af5e48f1f` | 4211 | file inventory |
| `apps/web/src/styles/tokens.css` | `0b6a16dc9c4d40bcd8c526145ddbf2b80ff73b7f` | 2488 | file inventory |
| `apps/web/src/test/setup.ts` | `33912b84ce78a7e1b763fcd8b7408ca29ec16001` | 613 | file inventory |
| `apps/web/src/vite-env.d.ts` | `618e4ddb0b871f6b4c375f550009d543e9b2a0ff` | 267 | file inventory |
| `apps/web/tsconfig.app.json` | `3b85a9c0911fbf2abea504b87fc335be0cad9420` | 824 | file inventory |
| `apps/web/tsconfig.e2e.json` | `6ee417244b5e5a1636474cba9c19b0421e577345` | 603 | file inventory |
| `apps/web/tsconfig.json` | `371e29bc9f519368737a6d5b1cf2c514d5dc2c2d` | 188 | file inventory |
| `apps/web/tsconfig.node.json` | `c67f20531bfe0a58e9ef9c96649b6d61b34f3893` | 391 | file inventory |
| `apps/web/vite.config.ts` | `9c46addccc66bd57951ea6b6833bb6301f291336` | 2053 | file inventory |
| `backend/.env.example` | `88d6e4ba3bcb44494475f675ad16703d73a47376` | 425 | file inventory |
| `backend/README.md` | `248356f5694f8bfdb4e775eb50df12be19e58b86` | 2552 | file inventory |
| `backend/adapters/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/adapters/routeros/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/adapters/routeros/apiclient.py` | `fd4400a0959ede46915c595ad5aa5ed209743400` | 13130 | AST + file inventory |
| `backend/adapters/routeros/base.py` | `6e9dbc32dd0fdc3294b36b7b8286e7e260dc7eb5` | 3736 | AST + file inventory |
| `backend/adapters/routeros/factory.py` | `8b90506d2b61c3276f726dbb70b1296d545937ba` | 1367 | AST + file inventory |
| `backend/adapters/routeros/simulator.py` | `40c67d5a791fad9abeaa0ef0f2a9bdf9392989e6` | 10697 | AST + file inventory |
| `backend/domains/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/audit/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/audit/apps.py` | `551e078fa8ce1208d241883cc9531f7dd64868ca` | 113 | AST + file inventory |
| `backend/domains/audit/migrations/0001_initial.py` | `811740bad176d459008495c159c7f5fc5d8de68f` | 1306 | AST + file inventory |
| `backend/domains/audit/migrations/0002_initial.py` | `6bc8534bb625c47321e6a640a6b06c1a907daf92` | 934 | AST + file inventory |
| `backend/domains/audit/migrations/0003_rls.py` | `7dd612c8c120842346dc167e254a7de32413b3ad` | 494 | AST + file inventory |
| `backend/domains/audit/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/audit/models.py` | `ec38a73b2543bd86f61b32c5879a52ec61546952` | 2766 | AST + file inventory |
| `backend/domains/audit/urls.py` | `2cc9be40278e0ec815312630e3df36584155acb4` | 191 | AST + file inventory |
| `backend/domains/audit/views.py` | `ffdd5970f1b23c50ca088b28e25e2320a4307f95` | 1789 | AST + file inventory |
| `backend/domains/backups/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/backups/apps.py` | `35927747ca3182cca5179f9e6ee2fbbd73546471` | 503 | AST + file inventory |
| `backend/domains/backups/migrations/0001_initial.py` | `f9312b4e301f751943bf8bdbae53cce7122a52f0` | 3515 | AST + file inventory |
| `backend/domains/backups/migrations/0002_rls_composite.py` | `66742bc6eecb05596f1bba71151efc3392802d6a` | 1440 | AST + file inventory |
| `backend/domains/backups/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/backups/models.py` | `be1b50fc952b0fcf63813b0b6264e0d43d57c325` | 4608 | AST + file inventory |
| `backend/domains/backups/service.py` | `6c541ea62bd52656ef610fdca4c12d4c31748244` | 12097 | AST + file inventory |
| `backend/domains/backups/urls.py` | `94fb8ba88cc25a4075ebce48fa7d81c4906c924d` | 458 | AST + file inventory |
| `backend/domains/backups/views.py` | `ce44973d4badbd83e13bb68c7238794ab479df69` | 6238 | AST + file inventory |
| `backend/domains/billing/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/billing/apps.py` | `ed0f24588893481dd03deef174409b6c7f4757c4` | 185 | AST + file inventory |
| `backend/domains/billing/calendar.py` | `92a8b07d22b350efd79e837804e6c077dbad3d04` | 7773 | AST + file inventory |
| `backend/domains/billing/management/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/billing/management/commands/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/billing/management/commands/issue_due_invoices.py` | `fc6b6fb7ed2cb97358126e431014592e6d632946` | 6160 | AST + file inventory |
| `backend/domains/billing/management/commands/seed_billing_e2e.py` | `c725eb09b165c86e58afabf21a19dcf444483723` | 7732 | AST + file inventory |
| `backend/domains/billing/migrations/0001_initial.py` | `d1fa16569c8e199ca6dcd68dd4413564dfa4c8cc` | 13875 | AST + file inventory |
| `backend/domains/billing/migrations/0002_rls_composite.py` | `d0f3fbc6eb5c6a255bf0e6561e081a4f87857298` | 2778 | AST + file inventory |
| `backend/domains/billing/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/billing/models.py` | `cac5543a83cacc1d260f5874b9e100a79e465c68` | 15480 | AST + file inventory |
| `backend/domains/billing/services.py` | `fa25e392eaafa84ba0188f6cb9ca638a889d4759` | 30922 | AST + file inventory |
| `backend/domains/billing/urls.py` | `46dadfefe373a71dd61344e3ae2f8947132dc806` | 2224 | AST + file inventory |
| `backend/domains/billing/views.py` | `ff9f3cba95fba3fa3688aa243de820403bd114b8` | 20305 | AST + file inventory |
| `backend/domains/common/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/common/crypto.py` | `3bffacd41973f7dc371e1938b8d9c18ac9285870` | 2632 | AST + file inventory |
| `backend/domains/common/envelope.py` | `cc9e66370040ecaf139ee25743489b842c470b6e` | 6691 | AST + file inventory |
| `backend/domains/common/idempotency.py` | `9fe430c0db64c665c51189154b04fbff81c2459a` | 3594 | AST + file inventory |
| `backend/domains/common/middleware.py` | `77c349c7abcabaae404e96be54c5b299f2531941` | 1818 | AST + file inventory |
| `backend/domains/common/migration_sql.py` | `d95983220abf7c3158a4a0a540718b12b02a964a` | 2059 | AST + file inventory |
| `backend/domains/common/pagination.py` | `850860bdc0e42e77e2148733763ab8ff7cd6cdf9` | 2031 | AST + file inventory |
| `backend/domains/common/tenant_context.py` | `aab8644b5a669b8655dc0ec9743874542abdb50f` | 3047 | AST + file inventory |
| `backend/domains/common/views.py` | `19872325ecb0a589f5b4c79d36b897e163873ef9` | 5455 | AST + file inventory |
| `backend/domains/config/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/config/apps.py` | `093ba66987cadb35e51489c36004e3af9e4899b5` | 116 | AST + file inventory |
| `backend/domains/config/branding.py` | `18d0ca6431eb352c9cd36bfc5e9256401de4c01b` | 1543 | AST + file inventory |
| `backend/domains/config/management/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/config/management/commands/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/config/management/commands/grant_runtime.py` | `8a090036725ade083a2ec847dad9b653b7286141` | 3221 | AST + file inventory |
| `backend/domains/config/management/commands/seed_dev.py` | `823adff11405da5dc392d8cb1ce03b6a174e48db` | 2775 | AST + file inventory |
| `backend/domains/config/registry.py` | `65817c06018c5c05dd589a22a46abe8faed39d15` | 4249 | AST + file inventory |
| `backend/domains/config/urls.py` | `bdff18fa92481df8794b3535f6d1ecf0f8b4b8f7` | 461 | AST + file inventory |
| `backend/domains/config/views.py` | `0de50956d95e227910f72b25523ba58281059eeb` | 3025 | AST + file inventory |
| `backend/domains/customers/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/customers/apps.py` | `4ec8466da313575163384b441eb330c491d4af13` | 558 | AST + file inventory |
| `backend/domains/customers/handlers.py` | `29e30f85297c12058fd32e0cb9440a36322981dd` | 5571 | AST + file inventory |
| `backend/domains/customers/migrations/0001_initial.py` | `a7d259f902ba666b40eedf8ee8f0c29895c321db` | 11857 | AST + file inventory |
| `backend/domains/customers/migrations/0002_rls_composite.py` | `10c78f8f798ec06f9db3ab8ee1bb9b3570f61c0a` | 3039 | AST + file inventory |
| `backend/domains/customers/migrations/0003_customer_locale_service_billing_package.py` | `7eac61751f845fab1884fc8355fb6644068a6d2b` | 778 | AST + file inventory |
| `backend/domains/customers/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/customers/models.py` | `c82f75e7ea870bb96e992ea60d7370fb06000a7f` | 12780 | AST + file inventory |
| `backend/domains/customers/services.py` | `fa1b5baf7ab3898cef99b3aa38d08f45beb10a20` | 39719 | AST + file inventory |
| `backend/domains/customers/urls.py` | `909138828a3423c5edf91a491a059bc6af7d2b28` | 2494 | AST + file inventory |
| `backend/domains/customers/views.py` | `90c3c5941d807bd45c4fb5d7248b1e0aa0c412d9` | 28017 | AST + file inventory |
| `backend/domains/documents/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/documents/apps.py` | `b01ca4e3ae8601f5192531173fb11db8a5757be0` | 200 | AST + file inventory |
| `backend/domains/documents/migrations/0001_initial.py` | `3eef63b30c8046286656667ac0a4c8a03034551e` | 2499 | AST + file inventory |
| `backend/domains/documents/migrations/0002_rls_immutable.py` | `c8a4284653d5092e69397e944b7f948d8e1d8ac2` | 1529 | AST + file inventory |
| `backend/domains/documents/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/documents/models.py` | `327900e7ba3e238e55e7b1d136c7b58e36bf04c4` | 3163 | AST + file inventory |
| `backend/domains/documents/rendering.py` | `97549d87a30ff66a900367a76bb6573e43fae7a1` | 11192 | AST + file inventory |
| `backend/domains/documents/services.py` | `f2e65af42fc27cc986302f6fa013fac8071beb28` | 5792 | AST + file inventory |
| `backend/domains/documents/urls.py` | `3a6f7000e0eef982c8bd088068e9496a2ea6acf5` | 541 | AST + file inventory |
| `backend/domains/documents/views.py` | `41fcea19a48c9dce26a2ed4fa4253724afc81ce7` | 4272 | AST + file inventory |
| `backend/domains/i18n/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/i18n/apps.py` | `67d5dd878313c8059cbc99de8c5b5830b013128c` | 110 | AST + file inventory |
| `backend/domains/i18n/catalogs.py` | `f1e3c9f31779d4aa8e1583d26ebb4f30a64ba328` | 9203 | AST + file inventory |
| `backend/domains/i18n/enums.py` | `7115fb939260e4abf4fe505dfd710ec5d63e2cfa` | 2275 | AST + file inventory |
| `backend/domains/identity/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/identity/apps.py` | `3a06a469ba74c9efb3971a93d9a543f638908937` | 122 | AST + file inventory |
| `backend/domains/identity/authentication.py` | `8b742f15e31cc13d0d9e4cba3e66365f11d780a2` | 1534 | AST + file inventory |
| `backend/domains/identity/migrations/0001_initial.py` | `92cda5e8cd628ef4910e8329fc45b21cf28dab8c` | 6401 | AST + file inventory |
| `backend/domains/identity/migrations/0002_initial.py` | `90d20d22367add647f4baef987c7066481b361c9` | 1368 | AST + file inventory |
| `backend/domains/identity/migrations/0003_emailtoken_meta.py` | `8217c213e2b506ba058a4b27f7c11b5da2b7e9b1` | 376 | AST + file inventory |
| `backend/domains/identity/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/identity/models.py` | `118ad90ff35de5c399a431197e87ce9bc1fd5f15` | 6192 | AST + file inventory |
| `backend/domains/identity/serializers.py` | `4c2b5442c359ee37a0e41e2cbfc5f2437fecb65e` | 682 | AST + file inventory |
| `backend/domains/identity/services.py` | `a34ca9e3b7ae06c5e9404a1bef83a04032c9de6f` | 15127 | AST + file inventory |
| `backend/domains/identity/totp.py` | `7393b912f5521f44217890a774cbc3a71c9b7674` | 2371 | AST + file inventory |
| `backend/domains/identity/urls.py` | `10767ae008094844263027ca5292caea3e266dca` | 1083 | AST + file inventory |
| `backend/domains/identity/views.py` | `01e095cba4fe5717be792228aad5077ba3813846` | 6431 | AST + file inventory |
| `backend/domains/jobs/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/jobs/apps.py` | `021ef2d52cbe90793409ac5bf27f94d2f181f5ab` | 110 | AST + file inventory |
| `backend/domains/jobs/engine.py` | `7731e41f0df922ec17129df58f73f46978b636fc` | 14980 | AST + file inventory |
| `backend/domains/jobs/management/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/jobs/management/commands/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/jobs/management/commands/runworker.py` | `0f10770fad7ea521c7d34d8ca1e78514db3b3880` | 2034 | AST + file inventory |
| `backend/domains/jobs/migrations/0001_initial.py` | `9985e006b6c5714e801fa53512ad63223ec42fd9` | 7793 | AST + file inventory |
| `backend/domains/jobs/migrations/0002_rls_composite.py` | `60a2dc870f80a9ea0cfbb96f9bdca4fa84a8eefe` | 1040 | AST + file inventory |
| `backend/domains/jobs/migrations/0003_alter_job_kind.py` | `f77e3fb1c9eba2d2c7c671f7abe15f7916418ca7` | 1240 | AST + file inventory |
| `backend/domains/jobs/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/jobs/models.py` | `27697f564c5df5b01be89ef64aa654b0ed46413d` | 9167 | AST + file inventory |
| `backend/domains/jobs/urls.py` | `3a92c9256b77e148aaf39562c259a6c90405bca3` | 423 | AST + file inventory |
| `backend/domains/jobs/views.py` | `cd0ed0b80882357cb5d0a7733012175b82d46afe` | 3995 | AST + file inventory |
| `backend/domains/monitoring/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/monitoring/apps.py` | `4239381f963d6469d8a3cb6177134d4130a6473d` | 128 | AST + file inventory |
| `backend/domains/monitoring/urls.py` | `9a9b10bc3b305b034dfd2b3f50a9e42cb8b7ff5a` | 180 | AST + file inventory |
| `backend/domains/monitoring/views.py` | `a08f7b5d1a7630ccd709f9614bfa727f18950321` | 4839 | AST + file inventory |
| `backend/domains/network/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/network/apps.py` | `1c11e1f4837845df247c482faaac8fb2ec5d5ebd` | 309 | AST + file inventory |
| `backend/domains/network/handlers.py` | `be5cf2fbbf2a177fc8c5cc57004a3a313a995311` | 8001 | AST + file inventory |
| `backend/domains/network/management/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/network/management/commands/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/network/management/commands/adopt_wg_host.py` | `bd2ef9372e346979be8e0be7514dac8b839d04b3` | 1097 | AST + file inventory |
| `backend/domains/network/management/commands/probe_wg.py` | `7737c24138466966542afc97ad91088e29c8a669` | 1359 | AST + file inventory |
| `backend/domains/network/management/commands/render_wg_config.py` | `c13884247cd73af1b3638cef546f4118dbea84a5` | 1243 | AST + file inventory |
| `backend/domains/network/migrations/0001_initial.py` | `cf682e66101850c86645f82d0f1b1b735a799758` | 4150 | AST + file inventory |
| `backend/domains/network/migrations/0002_rls_composite.py` | `58015b34bf42b64c70d0a818ed33784950c6beb0` | 734 | AST + file inventory |
| `backend/domains/network/migrations/0003_wireguardhost_router_api_cert_fingerprint_and_more.py` | `fd045819fe4095c6e5511c3cd79bfacd09c15fac` | 11903 | AST + file inventory |
| `backend/domains/network/migrations/0004_rls_m3.py` | `9fda54f05bad0f48ac0529b44cf4cd348305cc02` | 2465 | AST + file inventory |
| `backend/domains/network/migrations/0005_alter_discoveryobject_snapshot.py` | `2158784222a0ac18e1d9bbafe822971cf22a33ed` | 541 | AST + file inventory |
| `backend/domains/network/migrations/0006_routerenrollment_token_ref.py` | `46d1f38f9e6e2c7c3abda5e8efe2bf7e7968132a` | 419 | AST + file inventory |
| `backend/domains/network/migrations/0007_enroll_bridge_policy.py` | `2c7f7dd8b3a6d50a528ec7f2890284472db07e2b` | 914 | AST + file inventory |
| `backend/domains/network/migrations/0008_alter_wireguardpeer_router.py` | `84a282f3bc394fcaa48baf05965c174026d679bc` | 554 | AST + file inventory |
| `backend/domains/network/migrations/0009_wireguardhost_adopted_at_wireguardhost_key_source.py` | `800bab220ed85b255dd49cd83860a78587a5468e` | 685 | AST + file inventory |
| `backend/domains/network/migrations/0010_routerenrollment_protocol_and_more.py` | `f56a0f4edc0b4a978b3530f240634c3f5ab296a2` | 926 | AST + file inventory |
| `backend/domains/network/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/network/models.py` | `19a72020fc58fba32882d7af37b841c96b58b272` | 16734 | AST + file inventory |
| `backend/domains/network/services.py` | `fe4e62352c04ae2e902cc640c7898db10f1f0bae` | 42309 | AST + file inventory |
| `backend/domains/network/urls.py` | `d2163ed351a69eb679d95b9e2a7c96d48f60a01b` | 1381 | AST + file inventory |
| `backend/domains/network/views.py` | `63605759d200a16ee0a7fd348417958532a47448` | 9974 | AST + file inventory |
| `backend/domains/radius/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/radius/apps.py` | `8805f82c78bc4c42e649d50adad49b0105df759e` | 1401 | AST + file inventory |
| `backend/domains/radius/handlers.py` | `58f54539a8f3f9b48623682c08c2a66ba50525bf` | 12086 | AST + file inventory |
| `backend/domains/radius/harness/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/radius/harness/udp_relay.py` | `18cf74462a5fcfaa7f5a2910eb57654f16ac20f9` | 3245 | AST + file inventory |
| `backend/domains/radius/management/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/radius/management/commands/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/radius/management/commands/render_radius_config.py` | `f3f797a39b7b28ed7d6e8e2d03a53c21837646b6` | 2863 | AST + file inventory |
| `backend/domains/radius/management/commands/seed_radius_check.py` | `e0a090f4346f75bf9ddfa3f5fe2b8a8b3d16e3f4` | 5550 | AST + file inventory |
| `backend/domains/radius/management/commands/setup_radius.py` | `049704a465c2fe46162208eaa74b2d784d669789` | 1853 | AST + file inventory |
| `backend/domains/radius/migrations/0001_radius_schema.py` | `fc1581d2d92c6cb2aedd7086bef3ca1aa17001b4` | 8279 | AST + file inventory |
| `backend/domains/radius/migrations/0002_facade_functions.py` | `029137003d394cdf4cd0c87e1a5fcc3cae5fcf89` | 14140 | AST + file inventory |
| `backend/domains/radius/migrations/0003_initial.py` | `e14cd2053e20eb867dbdd09b827446f3cd2be772` | 7951 | AST + file inventory |
| `backend/domains/radius/migrations/0004_cutover_run_rls.py` | `9f5a5c6da11098b11481dbb90427a3204b634d41` | 1454 | AST + file inventory |
| `backend/domains/radius/migrations/0005_facade_row_shape_rlm_sql.py` | `9f0abc6601a217ce21d7dd37890ef2e92fd9a557` | 5034 | AST + file inventory |
| `backend/domains/radius/migrations/0006_session_key_and_session_list.py` | `dfbd297b80230922ea56082974a8eed2b9258a9a` | 11822 | AST + file inventory |
| `backend/domains/radius/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/radius/models.py` | `e220ab5a694284a3bc267e843bc152fdc36f3fbd` | 9772 | AST + file inventory |
| `backend/domains/radius/projection.py` | `d976f963a2bce6318dfb02ca1ecbe24575876e07` | 7069 | AST + file inventory |
| `backend/domains/radius/reconciler.py` | `8b09e57015e691f9df228021e1860ce53de14b36` | 11619 | AST + file inventory |
| `backend/domains/radius/services.py` | `6c50b5448126a9b4ca0cd9d3daba63372e909d0c` | 3982 | AST + file inventory |
| `backend/domains/radius/urls.py` | `86146d5e75c12fd5195264a0bd11a11a524d711f` | 499 | AST + file inventory |
| `backend/domains/radius/views.py` | `88bc9fa210a1ab529b1101e47a98dbeb90f35786` | 2317 | AST + file inventory |
| `backend/domains/subscriptions/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/subscriptions/apps.py` | `b4ac27ae1e1473f2d7e94ceb800dd145772c3506` | 137 | AST + file inventory |
| `backend/domains/subscriptions/migrations/0001_initial.py` | `d411217b04819f24a0fb621c2e2577143d116141` | 9322 | AST + file inventory |
| `backend/domains/subscriptions/migrations/0002_rls_composite.py` | `4743bcc5a3baa251e306698c5339c0a75ddb8e60` | 1695 | AST + file inventory |
| `backend/domains/subscriptions/migrations/0003_paymentsubmission_reviewed_by.py` | `9d94cb3e0a33e8fc10abf5c98a06ba8627695a4a` | 680 | AST + file inventory |
| `backend/domains/subscriptions/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/subscriptions/models.py` | `c2c7f2ccc0caa828255e1147b6c930a592575b5c` | 8475 | AST + file inventory |
| `backend/domains/subscriptions/services.py` | `a8ecd06667b21442955724e83b87ce6d6fe987e1` | 17048 | AST + file inventory |
| `backend/domains/subscriptions/upload.py` | `06720b8666cd96de8dd202636d39a57189d49548` | 4437 | AST + file inventory |
| `backend/domains/subscriptions/urls.py` | `8fc2cf73e2fbf5c1e567b8dbdd40f81616eb3dff` | 1330 | AST + file inventory |
| `backend/domains/subscriptions/views.py` | `d985fadde0a289dc6711569b28d13b57e68e600f` | 8935 | AST + file inventory |
| `backend/domains/tenancy/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/tenancy/apps.py` | `7b54612effa3d17e86096337ae0a4ec53202080f` | 148 | AST + file inventory |
| `backend/domains/tenancy/migrations/0001_initial.py` | `da82e23dfc043b498558d1331203c553465fb5a9` | 2553 | AST + file inventory |
| `backend/domains/tenancy/migrations/0002_locale.py` | `c96d42c7e7f93385d806ef5490770400005e8e8b` | 587 | AST + file inventory |
| `backend/domains/tenancy/migrations/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/domains/tenancy/models.py` | `5893643d933663318990e670f71a4bcc0939f2eb` | 2855 | AST + file inventory |
| `backend/domains/tenancy/permissions.py` | `0a641a969a3fa5481f62cffd9b8e0c83218df4e7` | 2673 | AST + file inventory |
| `backend/infra/postgres/bootstrap_dev.sql` | `625bb774e5f97e1cdd48b673f8916494d26fefdf` | 702 | file inventory |
| `backend/manage.py` | `0836da414a1a30256b1e4d53a55f4267491a3ae6` | 659 | AST + file inventory |
| `backend/microtix/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/microtix/asgi.py` | `4fed22269b9c4d55cf21c5e46851300ceee94840` | 169 | AST + file inventory |
| `backend/microtix/dburl.py` | `00b7abfa486d7bd8cbb31f28881110d5532da984` | 1830 | AST + file inventory |
| `backend/microtix/settings.py` | `1d7f51c9cf49b53857550146d2942c94abe660ff` | 8613 | AST + file inventory |
| `backend/microtix/settings_test.py` | `b95fa0f31beb0d7ae5372244b011878562b81da4` | 1286 | AST + file inventory |
| `backend/microtix/urls.py` | `cad21c3a6c27deb917e45b379014c15dd92ce72c` | 1359 | AST + file inventory |
| `backend/microtix/wg.py` | `5e0f8267adf73592e8c2a56252a0d4ad89140047` | 1001 | AST + file inventory |
| `backend/microtix/wsgi.py` | `2d44d86658ef02cc279160c2279848491eb39f28` | 169 | AST + file inventory |
| `backend/pyproject.toml` | `6bd82b7291161f430dbccdae242a2aebdfeb17b4` | 1288 | file inventory |
| `backend/pytest.ini` | `e6fe208f204728a46ab3eb902d5966082073a09b` | 322 | file inventory |
| `backend/scripts/dev_bootstrap.sh` | `e568d6da9bc6535e4e3b8d6b0e27aba7f6ae29f7` | 3449 | file inventory |
| `backend/scripts/test_radius.sh` | `4463b587014bd4cf6a32f631eff606443b5802aa` | 20930 | file inventory |
| `backend/tests/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/tests/conftest.py` | `5ea65638daef98187a00977ecda190cc824329b2` | 3823 | AST + file inventory |
| `backend/tests/contracts/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/tests/contracts/test_api_contract.py` | `3127f2148b29761bd1bce14ada03816240f6137a` | 3555 | AST + file inventory |
| `backend/tests/contracts/test_billing_contract.py` | `eca17c48f98c247616372d1d7261551695a64a85` | 2366 | AST + file inventory |
| `backend/tests/contracts/test_customers_contract.py` | `e36eb5957e3f76632bbc4ddd9344556f6278ef65` | 9507 | AST + file inventory |
| `backend/tests/contracts/test_ops_contract.py` | `8172f4c1ec7e5d4479ea14ef1aad0b3eeb8c3777` | 6604 | AST + file inventory |
| `backend/tests/contracts/test_radius_contract.py` | `62c2415770ef8c583deab421856ae454d5f7d7d0` | 3373 | AST + file inventory |
| `backend/tests/integration/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/tests/integration/test_auth_flow.py` | `3c362c6e9c06c0555b4dbc0ed856757b655af04c` | 8032 | AST + file inventory |
| `backend/tests/integration/test_billing_invoice_flow.py` | `9d4ec11ea181e053af2d6d4d547967a400de6514` | 23864 | AST + file inventory |
| `backend/tests/integration/test_billing_payments.py` | `69b4dfdb80619a709077393ec99eb3fa21f3a4b3` | 26614 | AST + file inventory |
| `backend/tests/integration/test_customers_api.py` | `e6bb824b8283ad46258659e326d79550c4914a4c` | 25137 | AST + file inventory |
| `backend/tests/integration/test_documents_api.py` | `122777d699b411f6cb269f4aa7c27bae60db8b81` | 15974 | AST + file inventory |
| `backend/tests/integration/test_enrollment_flow.py` | `384ef201be15224dc624ea945ead18ff270c5793` | 24071 | AST + file inventory |
| `backend/tests/integration/test_idempotency_quota.py` | `1207867e2c113ff00d97f2f1b38b31dc2f517b5e` | 5293 | AST + file inventory |
| `backend/tests/integration/test_jobs_engine.py` | `1e9e24116c595e27328c69a0d509bab9009ced47` | 6475 | AST + file inventory |
| `backend/tests/integration/test_migration_flow.py` | `c75a070e4f10e3a2fabae020cb6ac866444294e4` | 15299 | AST + file inventory |
| `backend/tests/integration/test_ops_backups.py` | `e83ec09dbb2016edd2ab15ee2c7e3a45b43baf24` | 11373 | AST + file inventory |
| `backend/tests/integration/test_ops_monitor.py` | `475090738b3c037c043c4ca1ae8de73bae4d6854` | 4189 | AST + file inventory |
| `backend/tests/integration/test_ops_platform_admin.py` | `eab9f1d71acfa075786edbc7b7a44c0a2fc5126a` | 12992 | AST + file inventory |
| `backend/tests/integration/test_radius_cutover.py` | `afe46f714e28819f11e926622343ad2b1acc8ef5` | 6923 | AST + file inventory |
| `backend/tests/integration/test_radius_facade.py` | `eb500ae20477f9205572ca7e34b744a1ffb55017` | 6087 | AST + file inventory |
| `backend/tests/integration/test_radius_projection.py` | `0c242e7c0e7d745c37dd0c0d69d8305cd55b1c48` | 6204 | AST + file inventory |
| `backend/tests/integration/test_rls.py` | `863f83635ee7e31d86248ad21bf8df09c54fd0bd` | 3390 | AST + file inventory |
| `backend/tests/integration/test_wg_host.py` | `95f3a8a3cdd76b471b74381417af42b5cb5fa647` | 12729 | AST + file inventory |
| `backend/tests/unit/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | AST + file inventory |
| `backend/tests/unit/test_apiclient.py` | `60a114d24fac321d64ad0cfabca2f6a20e42e0a6` | 7357 | AST + file inventory |
| `backend/tests/unit/test_audit_permissions.py` | `fb7842ca08d947884c65ba526320cf56d2dac122` | 1992 | AST + file inventory |
| `backend/tests/unit/test_billing_calendar.py` | `bc35f4e6b1b36759435a9fcc62cc20c61bef2291` | 12827 | AST + file inventory |
| `backend/tests/unit/test_crypto.py` | `ce5ac2b5002bdb0a74fcada5c0bff7a44f5a2e5a` | 1269 | AST + file inventory |
| `backend/tests/unit/test_customers_models.py` | `bc9136758667ddd037e6a82953b663a81bc74b51` | 9190 | AST + file inventory |
| `backend/tests/unit/test_documents_render.py` | `af27d98f4067903a3ecdaa24f607ba990689ad02` | 7882 | AST + file inventory |
| `backend/tests/unit/test_radius_config.py` | `b2477a6defe8f39fb852c0a088f79d76498c588f` | 6287 | AST + file inventory |
| `backend/tests/unit/test_registry_pagination.py` | `108bcab9bd911d2a32ad29321121fd190626ecb1` | 2184 | AST + file inventory |
| `backend/tests/unit/test_simulator.py` | `7eafb01247f3d7b3a567b32eb157dd08b2ac5800` | 3559 | AST + file inventory |
| `backend/tests/unit/test_state_machine.py` | `22e427e850a014e13ae07dd0846a99bad5bcf9fe` | 1440 | AST + file inventory |
| `backend/tests/unit/test_totp.py` | `1faff69584f512b875aa63c3dbede0255e58ee70` | 2197 | AST + file inventory |
| `backend/tests/unit/test_wg_probe.py` | `a1aa6cacd29ba5f21b00ad72bd47a9729d306845` | 2881 | AST + file inventory |
| `docs/ACCEPTANCE.md` | `42c9b3f24dce4304fb020ce7a3e9ed8a9a5fc688` | 10546 | file inventory |
| `docs/ACS.md` | `4b042d25599e4548d51f301784083a27e029c3f1` | 12116 | file inventory |
| `docs/AGENT_HANDOFF.md` | `2af98f320eb2760781276e603feead2a348a69b8` | 8650 | file inventory |
| `docs/ARCHITECTURE.md` | `de4c8b0b5992f109b99e5b6b0041c406d120dc23` | 24459 | file inventory |
| `docs/AUDIT_REPORT.md` | `ddf54b28bdd8776873378f5f7109d25853cc0d63` | 22515 | file inventory |
| `docs/BETA_RELEASE_STATUS.md` | `9ec9e511857f7d2245bc0149811733a24566160a` | 12357 | file inventory |
| `docs/BETA_TEST_EVIDENCE.md` | `04db5b63201a57555cd468a2a94871bee938b163` | 7562 | file inventory |
| `docs/FINANCE.md` | `7e063b61b0fd565889f7e81552da25512083ede7` | 15181 | file inventory |
| `docs/I18N.md` | `02be91eb7bd56a4a12f7515bce31050de37dab75` | 7134 | file inventory |
| `docs/IMPLEMENTATION_PLAN.md` | `153408d4d9039e5f453933f7e6d3ca6aa39c4254` | 8964 | file inventory |
| `docs/MASTER_PROMPT.md` | `33de90508fb7b6d3138d92cf8edcb9cd46632f9c` | 8155 | file inventory |
| `docs/OPERATIONS.md` | `6a9ec0e113d9c4cd71a96f9d77b28b79bc4eca38` | 11012 | file inventory |
| `docs/PRODUCT.md` | `6e9325dba92201b33d95ac40195d17a26b8ed66c` | 71154 | file inventory |
| `docs/RADIUS.md` | `b3d06b34ca4ed12a1410864923b47f6293676d22` | 24570 | file inventory |
| `docs/README.md` | `87ac61c0c808c61c3c34d05788bb92eab682d046` | 3010 | file inventory |
| `docs/ROUTEROS.md` | `e25cf0511fda49a5c7db9e9fd84af6557b43f898` | 10956 | file inventory |
| `docs/UI_UX.md` | `dad4168b2f3d83086062a07b261b7d9dc5a7bd2a` | 36937 | file inventory |
| `docs/branding.json` | `7c9530fc37c73bbdbf0bef0575ddefe29f7f1071` | 1474 | file inventory |
| `docs/defaults.json` | `2c4bf742bf9a7ed66d6753b780fed57b6efa5dae` | 58954 | file inventory |
| `docs/progress.md` | `59d1c6eed894677d31501703a000f9c690c67775` | 52368 | file inventory |
| `docs/repository-manifest.json` | `c480b9d2a5e38f2d18bf07cab53195333655b672` | 3696 | file inventory |
| `docs/tasks.json` | `ee345386cf0f7e1bbfbb6be5c5726e713c2c1037` | 69135 | file inventory |
| `docs/test-cases.json` | `91d81056c8757e10a946069142314731a070760d` | 224711 | file inventory |
| `docs/tools/check_docs.py` | `6f4d3f5ed44dda0dba921cfb3fe9b09a21958c3f` | 11320 | file inventory |
| `docs/tools/setup_env.sh` | `7cd9cbdfbb5425ad0b012fca9c68fa9eced63696` | 5150 | file inventory |
| `instalasi.sh` | `372768e6a5fe9c8d1baeefca10ac96100b9b8717` | 30408 | file inventory |
| `locales/en/web.json` | `ea8d156b0bd4f8090afc02c9aafbd06663b0da37` | 62891 | file inventory |
| `locales/id/web.json` | `0d07b0f7832df92585e30d8cd6df42b21819ffc9` | 63451 | file inventory |
| `report/LATEST_HANDOFF.md` | `9acca6c7103764cce4a989703bf8adca0089f3b9` | 9319 | file inventory |
| `report/backend-explorer/20261106T182013Z-router-onboarding-audit.md` | `8c8a349a567211ee2039296669d009d6a0e56601` | 27577 | file inventory |
| `report/backend-explorer/20261106TK604-api-contract.md` | `b9fe6f331171055d056b997c72230a549df6a4ee` | 33246 | file inventory |
| `report/documents-dev/20261106T145134Z-tk109-documents.md` | `f37e06be45d2401eeb53dbbad9c3ba240d4d5f94` | 13717 | file inventory |
| `report/frontend-explorer/20261106T181615Z-router-onboarding-ux-audit.md` | `090a479867e1087d3ad7ff93562f8c3a4d41e7a0` | 31463 | file inventory |
| `report/frontend-explorer/20261106TK604-fe-pattern.md` | `bb3b32557f420cbc6a5d2ae6c91b5795180fef7d` | 31878 | file inventory |
| `report/orchestrator/20261105T191826Z-wg-host-adoption.md` | `b18388ce2e0ff1aa04140c61b89e54603591efd7` | 5886 | file inventory |
| `report/orchestrator/20261105T191830Z-e2e-harness.md` | `12cbc5a2c10b8e4a8e2916e13dcd5236b9d07f46` | 4779 | file inventory |
| `report/orchestrator/20261106T063225Z-setup-env-inrepo-push.md` | `774932a5ce508eb435ad88cf09d12e4839573995` | 6917 | file inventory |
| `report/orchestrator/20261106T151951Z-billing-m6-tk601-docs-tk109.md` | `12bfa422e293bd681213dd41008b72d4065d04bd` | 9196 | file inventory |
| `report/orchestrator/20261106T174500Z-tk604-billing-ui.md` | `721afefbf9499a8e8d380eeb477521de6897ec1c` | 9296 | file inventory |
| `report/orchestrator/20261106T195642Z-phase1-wireguard-onboarding.md` | `0530377c2fc3c4fd233628a19f4d2d835acc4bad` | 14011 | file inventory |
| `report/researcher/20261106T183941Z-routeros-vpn-capability-matrix.md` | `5c6ee84298cd08f668e83531fb0f23029b55aaf8` | 40049 | file inventory |
| `report/reviewer/20261105T191840Z-independent-review.md` | `4db915fcaca7d10ece8281f54e22c177065d407e` | 5450 | file inventory |
| `report/reviewer/20261106T173900Z-tk604-independent-review.md` | `80790a03793a0a92c0ee5ea3004a4fb78168bbce` | 4028 | file inventory |
| `report/reviewer/20261106T194638Z-wg-onboarding-independent-review.md` | `a97a8a2f699ac785491cd3dd73fb131b4fcebf10` | 20951 | file inventory |

## Cross-domain import callsites

| Source → target | Callsites and scope |
|---|---|
| audit → common | `backend/domains/audit/views.py:8` (runtime/composition); `backend/domains/audit/views.py:9` (runtime/composition) |
| backups → common | `backend/domains/backups/service.py:26` (runtime/composition); `backend/domains/backups/views.py:18` (runtime/composition); `backend/domains/backups/views.py:19` (runtime/composition); `backend/domains/backups/views.py:20` (runtime/composition) |
| backups → config | `backend/domains/backups/service.py:27` (runtime/composition); `backend/domains/backups/views.py:21` (runtime/composition) |
| backups → jobs | `backend/domains/backups/apps.py:12` (runtime/composition); `backend/domains/backups/service.py:28` (runtime/composition); `backend/domains/backups/views.py:22` (runtime/composition) |
| backups → network | `backend/domains/backups/service.py:144` (runtime/composition); `backend/domains/backups/views.py:23` (runtime/composition) |
| backups → tenancy | `backend/domains/backups/views.py:101` (runtime/composition) |
| billing → audit | `backend/domains/billing/services.py:34` (runtime/composition) |
| billing → common | `backend/domains/billing/management/commands/issue_due_invoices.py:30` (management/seed); `backend/domains/billing/management/commands/seed_billing_e2e.py:31` (management/seed); `backend/domains/billing/services.py:44` (runtime/composition); `backend/domains/billing/views.py:32` (runtime/composition); `backend/domains/billing/views.py:33` (runtime/composition); `backend/domains/billing/views.py:34` (runtime/composition); `backend/domains/billing/views.py:35` (runtime/composition) |
| billing → config | `backend/domains/billing/management/commands/seed_billing_e2e.py:39` (management/seed) |
| billing → customers | `backend/domains/billing/management/commands/issue_due_invoices.py:31` (management/seed); `backend/domains/billing/management/commands/seed_billing_e2e.py:32` (management/seed); `backend/domains/billing/services.py:45` (runtime/composition); `backend/domains/billing/services.py:585` (runtime/composition); `backend/domains/billing/views.py:36` (runtime/composition) |
| billing → documents | `backend/domains/billing/services.py:46` (runtime/composition); `backend/domains/billing/services.py:47` (runtime/composition); `backend/domains/billing/services.py:48` (runtime/composition); `backend/domains/billing/views.py:37` (runtime/composition) |
| billing → identity | `backend/domains/billing/management/commands/seed_billing_e2e.py:33` (management/seed); `backend/domains/billing/management/commands/seed_billing_e2e.py:34` (management/seed) |
| billing → jobs | `backend/domains/billing/services.py:49` (runtime/composition) |
| billing → subscriptions | `backend/domains/billing/management/commands/seed_billing_e2e.py:35` (management/seed); `backend/domains/billing/services.py:54` (runtime/composition) |
| billing → tenancy | `backend/domains/billing/management/commands/issue_due_invoices.py:32` (management/seed); `backend/domains/billing/management/commands/seed_billing_e2e.py:36` (management/seed); `backend/domains/billing/services.py:50` (runtime/composition) |
| common → i18n | `backend/domains/common/envelope.py:16` (runtime/composition) |
| common → identity | `backend/domains/common/views.py:52` (runtime/composition) |
| common → jobs | `backend/domains/common/idempotency.py:20` (runtime/composition) |
| common → tenancy | `backend/domains/common/views.py:21` (runtime/composition); `backend/domains/common/views.py:22` (runtime/composition) |
| config → common | `backend/domains/config/management/commands/seed_dev.py:12` (management/seed); `backend/domains/config/registry.py:15` (runtime/composition); `backend/domains/config/views.py:16` (runtime/composition) |
| config → i18n | `backend/domains/config/views.py:19` (runtime/composition) |
| config → identity | `backend/domains/config/management/commands/seed_dev.py:13` (management/seed); `backend/domains/config/management/commands/seed_dev.py:14` (management/seed) |
| config → subscriptions | `backend/domains/config/management/commands/seed_dev.py:15` (management/seed); `backend/domains/config/management/commands/seed_dev.py:16` (management/seed) |
| config → tenancy | `backend/domains/config/management/commands/seed_dev.py:17` (management/seed) |
| customers → audit | `backend/domains/customers/services.py:884` (runtime/composition) |
| customers → common | `backend/domains/customers/handlers.py:9` (runtime/composition); `backend/domains/customers/services.py:22` (runtime/composition); `backend/domains/customers/services.py:23` (runtime/composition); `backend/domains/customers/services.py:24` (runtime/composition); `backend/domains/customers/views.py:19` (runtime/composition); `backend/domains/customers/views.py:20` (runtime/composition); `backend/domains/customers/views.py:21` (runtime/composition); `backend/domains/customers/views.py:22` (runtime/composition) |
| customers → jobs | `backend/domains/customers/apps.py:14` (runtime/composition); `backend/domains/customers/handlers.py:12` (runtime/composition); `backend/domains/customers/services.py:33` (runtime/composition); `backend/domains/customers/services.py:430` (runtime/composition); `backend/domains/customers/services.py:735` (runtime/composition); `backend/domains/customers/views.py:30` (runtime/composition) |
| customers → network | `backend/domains/customers/services.py:34` (runtime/composition); `backend/domains/customers/views.py:31` (runtime/composition) |
| customers → subscriptions | `backend/domains/customers/services.py:91` (runtime/composition); `backend/domains/customers/services.py:107` (runtime/composition); `backend/domains/customers/services.py:127` (runtime/composition); `backend/domains/customers/services.py:244` (runtime/composition); `backend/domains/customers/services.py:501` (runtime/composition); `backend/domains/customers/services.py:856` (runtime/composition) |
| documents → common | `backend/domains/documents/rendering.py:33` (runtime/composition); `backend/domains/documents/services.py:22` (runtime/composition); `backend/domains/documents/views.py:22` (runtime/composition); `backend/domains/documents/views.py:23` (runtime/composition); `backend/domains/documents/views.py:24` (runtime/composition) |
| documents → i18n | `backend/domains/documents/rendering.py:34` (runtime/composition) |
| identity → common | `backend/domains/identity/services.py:24` (runtime/composition); `backend/domains/identity/services.py:25` (runtime/composition); `backend/domains/identity/services.py:124` (runtime/composition); `backend/domains/identity/views.py:25` (runtime/composition) |
| identity → i18n | `backend/domains/identity/services.py:26` (runtime/composition) |
| identity → subscriptions | `backend/domains/identity/services.py:125` (runtime/composition) |
| identity → tenancy | `backend/domains/identity/services.py:29` (runtime/composition); `backend/domains/identity/services.py:30` (runtime/composition); `backend/domains/identity/services.py:369` (runtime/composition) |
| jobs → common | `backend/domains/jobs/engine.py:22` (runtime/composition); `backend/domains/jobs/views.py:15` (runtime/composition); `backend/domains/jobs/views.py:16` (runtime/composition); `backend/domains/jobs/views.py:17` (runtime/composition) |
| monitoring → common | `backend/domains/monitoring/views.py:21` (runtime/composition) |
| monitoring → config | `backend/domains/monitoring/views.py:22` (runtime/composition) |
| monitoring → network | `backend/domains/monitoring/views.py:23` (runtime/composition) |
| network → common | `backend/domains/network/handlers.py:39` (runtime/composition); `backend/domains/network/services.py:32` (runtime/composition); `backend/domains/network/services.py:33` (runtime/composition); `backend/domains/network/services.py:34` (runtime/composition); `backend/domains/network/views.py:10` (runtime/composition); `backend/domains/network/views.py:11` (runtime/composition); `backend/domains/network/views.py:12` (runtime/composition) |
| network → config | `backend/domains/network/services.py:390` (runtime/composition); `backend/domains/network/services.py:504` (runtime/composition); `backend/domains/network/services.py:535` (runtime/composition) |
| network → customers | `backend/domains/network/services.py:930` (runtime/composition); `backend/domains/network/views.py:39` (runtime/composition) |
| network → jobs | `backend/domains/network/handlers.py:6` (runtime/composition); `backend/domains/network/services.py:787` (runtime/composition); `backend/domains/network/views.py:13` (runtime/composition) |
| network → radius | `backend/domains/network/handlers.py:124` (runtime/composition) |
| network → tenancy | `backend/domains/network/services.py:96` (runtime/composition); `backend/domains/network/services.py:205` (runtime/composition); `backend/domains/network/services.py:568` (runtime/composition); `backend/domains/network/services.py:680` (runtime/composition) |
| radius → backups | `backend/domains/radius/handlers.py:75` (runtime/composition) |
| radius → common | `backend/domains/radius/management/commands/seed_radius_check.py:17` (management/seed); `backend/domains/radius/projection.py:20` (runtime/composition); `backend/domains/radius/views.py:9` (runtime/composition); `backend/domains/radius/views.py:10` (runtime/composition); `backend/domains/radius/views.py:11` (runtime/composition) |
| radius → customers | `backend/domains/radius/apps.py:17` (runtime/composition); `backend/domains/radius/handlers.py:70` (runtime/composition); `backend/domains/radius/handlers.py:89` (runtime/composition); `backend/domains/radius/management/commands/seed_radius_check.py:18` (management/seed); `backend/domains/radius/management/commands/seed_radius_check.py:19` (management/seed) |
| radius → identity | `backend/domains/radius/management/commands/seed_radius_check.py:20` (management/seed) |
| radius → jobs | `backend/domains/radius/apps.py:32` (runtime/composition); `backend/domains/radius/handlers.py:13` (runtime/composition); `backend/domains/radius/views.py:12` (runtime/composition) |
| radius → network | `backend/domains/radius/handlers.py:15` (runtime/composition); `backend/domains/radius/management/commands/seed_radius_check.py:21` (management/seed); `backend/domains/radius/services.py:13` (runtime/composition); `backend/domains/radius/services.py:70` (runtime/composition); `backend/domains/radius/services.py:80` (runtime/composition); `backend/domains/radius/views.py:13` (runtime/composition) |
| radius → tenancy | `backend/domains/radius/management/commands/seed_radius_check.py:23` (management/seed) |
| subscriptions → audit | `backend/domains/subscriptions/services.py:293` (runtime/composition) |
| subscriptions → common | `backend/domains/subscriptions/services.py:15` (runtime/composition); `backend/domains/subscriptions/services.py:107` (runtime/composition); `backend/domains/subscriptions/services.py:120` (runtime/composition); `backend/domains/subscriptions/services.py:165` (runtime/composition); `backend/domains/subscriptions/services.py:188` (runtime/composition); `backend/domains/subscriptions/services.py:247` (runtime/composition); `backend/domains/subscriptions/services.py:265` (runtime/composition); `backend/domains/subscriptions/services.py:409` (runtime/composition); `backend/domains/subscriptions/services.py:143` (runtime/composition); `backend/domains/subscriptions/services.py:155` (runtime/composition); `backend/domains/subscriptions/upload.py:16` (runtime/composition); `backend/domains/subscriptions/views.py:11` (runtime/composition); `backend/domains/subscriptions/views.py:12` (runtime/composition); `backend/domains/subscriptions/views.py:13` (runtime/composition) |
| subscriptions → jobs | `backend/domains/subscriptions/services.py:294` (runtime/composition); `backend/domains/subscriptions/services.py:351` (runtime/composition) |
| subscriptions → network | `backend/domains/subscriptions/services.py:84` (runtime/composition) |
| subscriptions → tenancy | `backend/domains/subscriptions/services.py:184` (runtime/composition); `backend/domains/subscriptions/services.py:248` (runtime/composition); `backend/domains/subscriptions/services.py:266` (runtime/composition) |

## Migration inventory

| Domain | Numbered migrations | Latest |
|---|---:|---|
| audit | 3 | `0003_rls.py` |
| backups | 2 | `0002_rls_composite.py` |
| billing | 2 | `0002_rls_composite.py` |
| common | 0 | NOT FOUND |
| config | 0 | NOT FOUND |
| customers | 3 | `0003_customer_locale_service_billing_package.py` |
| documents | 2 | `0002_rls_immutable.py` |
| i18n | 0 | NOT FOUND |
| identity | 3 | `0003_emailtoken_meta.py` |
| jobs | 3 | `0003_alter_job_kind.py` |
| monitoring | 0 | NOT FOUND |
| network | 10 | `0010_routerenrollment_protocol_and_more.py` |
| radius | 6 | `0006_session_key_and_session_list.py` |
| subscriptions | 3 | `0003_paymentsubmission_reviewed_by.py` |
| tenancy | 2 | `0002_locale.py` |

## Coverage and result limitations

Static parsing and inventory PASS are not pytest, Django checks, SQL migration application, RLS proof, compiler/typecheck, browser, installer, host, daemon, device, recovery or capacity test results. Those runtime operations were NOT_RUN in this documentation-only session. Repository source, historical reports and fetched CI metadata are separate evidence classes.
