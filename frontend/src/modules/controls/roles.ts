// Ruoli GRC abilitati alle azioni del modulo Controlli (rispecchiano le
// permission backend — security review 2026-06-12). Il claim `role` del JWT
// è il ruolo più alto dell'utente.

// SoAApprovalPermission: l'approvazione formale del SoA è un atto di governance
export const SOA_APPROVAL_ROLES = ["super_admin", "compliance_officer", "plant_manager"];

// ControlInstancePermission.write_roles: chi può assegnare l'owner di un controllo
export const OWNER_ASSIGN_ROLES = [...SOA_APPROVAL_ROLES, "control_owner"];
