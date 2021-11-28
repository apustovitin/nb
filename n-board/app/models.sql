drop schema public cascade;
create schema public;

create table news (
  id serial primary key,
  username varchar(40) not null,
  content text,
  timestamp timestamptz not null default current_timestamp
);
create index news_username on news using btree (username);
create index news_timestamp on news using btree (timestamp);
