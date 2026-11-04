-- Bloquant : doit renvoyer zéro ligne (une seule ligne par station, carburant et jour)
select
    id_station,
    carburant,
    jour,
    count(*) as nb
from {{ ref('stg_prix_carburants') }}
group by id_station, carburant, jour
having count(*) > 1