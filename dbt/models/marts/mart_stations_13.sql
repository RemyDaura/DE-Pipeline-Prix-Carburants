-- Stations des Bouches-du-Rhône au dernier jour disponible,
-- classées par prix pour chaque carburant (1 = la moins chère)
with dernier_jour as (
    select max(jour) as jour
    from {{ ref('int_prix_qualifies') }}
)

select
    p.jour,
    p.carburant,
    rank() over (partition by p.carburant order by p.prix) as rang,
    p.prix,
    p.prix_maj_le,
    p.id_station,
    p.adresse,
    p.cp,
    p.ville,
    p.pop,
    p.geom_lat,
    p.geom_lon,
    p.horaires_automate_24_24
from {{ ref('int_prix_qualifies') }} as p
inner join dernier_jour as d
    on p.jour = d.jour
where p.code_departement = '13'
    and p.est_recent
    and not p.est_suspect