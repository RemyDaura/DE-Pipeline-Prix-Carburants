-- Bloquant : un prix hors de 0,30 à 4,00 €/L est impossible
-- (erreur de format, prix en centimes...).
-- Bornes fixées le 2026-11-04 : prix observés entre 0,55 et 2,90 €/L.
select
    id_station,
    carburant,
    jour,
    prix
from {{ ref('stg_prix_carburants') }}
where prix < 0.30 or prix > 4.00