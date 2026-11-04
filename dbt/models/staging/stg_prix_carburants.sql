with source as (
    select * from {{ source('raw', 'prix_carburants') }}
),

-- Correspondance code département -> nom et région,
-- construite à partir des stations où la source les renseigne
referentiel_departements as (
    select distinct
        code_departement,
        departement,
        code_region,
        region
    from source
    where code_departement is not null
),

-- Le pipeline peut tourner plusieurs fois par jour :
-- on garde le dernier relevé de chaque station pour chaque jour
dernier_releve_du_jour as (
    select *
    from source
    where true
    qualify row_number() over (
        partition by id, date(extrait_le, 'Europe/Paris')
        order by extrait_le desc
    ) = 1
),

-- Une ligne par station et par carburant.
-- Les carburants sans prix ni date sont écartés automatiquement par UNPIVOT.
par_carburant as (
    select *
    from dernier_releve_du_jour
    unpivot (
        (prix, maj) for carburant in (
            (gazole_prix, gazole_maj) as 'Gazole',
            (sp95_prix, sp95_maj) as 'SP95',
            (sp98_prix, sp98_maj) as 'SP98',
            (e10_prix, e10_maj) as 'E10',
            (e85_prix, e85_maj) as 'E85',
            (gplc_prix, gplc_maj) as 'GPLc'
        )
    )
)

select
    p.id as id_station,
    date(p.extrait_le, 'Europe/Paris') as jour,
    p.carburant,
    p.prix,
    safe_cast(p.maj as timestamp) as prix_maj_le,
    p.adresse,
    p.cp,
    p.ville,
    -- Département manquant : déduit des 2 premiers chiffres du code postal,
    -- sauf Corse (20) et outre-mer (97), laissés vides faute de règle simple
    coalesce(p.code_departement, d.code_departement) as code_departement,
    coalesce(p.departement, d.departement) as departement,
    coalesce(p.code_region, d.code_region) as code_region,
    coalesce(p.region, d.region) as region,
    p.code_departement is null and d.code_departement is not null as departement_deduit_du_cp,
    p.pop,
    p.geom_lat,
    p.geom_lon,
    p.horaires_automate_24_24,
    p.extrait_le
from par_carburant as p
left join referentiel_departements as d
    on p.code_departement is null
    and d.code_departement = left(p.cp, 2)
    and not starts_with(p.cp, '20')
    and not starts_with(p.cp, '97')