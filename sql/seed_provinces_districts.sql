-- Provinces
insert into provinces (name) values
('Central'),('Eastern'),('North Central'),('Northern'),
('North Western'),('Sabaragamuwa'),('Southern'),('Uva'),('Western')
on conflict (name) do nothing;

-- Districts (mapped by province name)
insert into districts (province_id, name)
select p.id, d.name
from provinces p
join (values
  ('Western','Colombo'),
  ('Western','Gampaha'),
  ('Western','Kalutara'),

  ('Central','Kandy'),
  ('Central','Matale'),
  ('Central','Nuwara Eliya'),

  ('Southern','Galle'),
  ('Southern','Matara'),
  ('Southern','Hambantota'),

  ('Uva','Badulla'),
  ('Uva','Monaragala'),

  ('Sabaragamuwa','Ratnapura'),
  ('Sabaragamuwa','Kegalle'),

  ('North Western','Kurunegala'),
  ('North Western','Puttalam'),

  ('North Central','Anuradhapura'),
  ('North Central','Polonnaruwa'),

  ('Northern','Jaffna'),
  ('Northern','Kilinochchi'),
  ('Northern','Mannar'),
  ('Northern','Mullaitivu'),
  ('Northern','Vavuniya'),

  ('Eastern','Ampara'),
  ('Eastern','Batticaloa'),
  ('Eastern','Trincomalee')
) as d(province, name) on d.province = p.name
on conflict do nothing;
