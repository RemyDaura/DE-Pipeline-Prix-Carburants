-- Bloquant : une seule ligne par jour, département et carburant
select
    jour,
    code_departement,
    carburant,
    count(*) as nb
from {{ ref('mart_prix_jour_departement') }}
group by jour, code_departement, carburant
having count(*) > 1