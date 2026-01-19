-- Salon Database DDL
-- For: AI Voice Agent for Salon
-- Contains ENUMs, tables, constraints, and the extra columns requested.

-- ========== ENUM TYPES ==========
-- Booking status used by the voice agent and UI
CREATE TYPE booking_status AS ENUM (
  'pending',     -- created but not yet confirmed
  'confirmed',   -- confirmed
  'completed',   -- service completed
  'cancelled',   -- cancelled by customer or salon
  'no_show'      -- customer did not show up
);

-- Weekday enum for salon_hours (optional, easier to read than ints)
CREATE TYPE weekday AS ENUM (
  'monday','tuesday','wednesday','thursday','friday','saturday','sunday'
);

-- ========== TABLES ==========

-- Customers
CREATE TABLE customers (
  customer_id         serial PRIMARY KEY,
  name                text NOT NULL,
  email               text UNIQUE,                       -- added: for confirmations/reminders
  phone_number        character varying(15),
  created_at          timestamp without time zone NOT NULL DEFAULT now()
);

-- Salon hours (weekly schedule)
CREATE TABLE salon_hours (
  salon_hours_id      serial PRIMARY KEY,
  day_of_week         weekday NOT NULL,                   -- using enum for readability
  open_time           time without time zone NOT NULL,
  close_time          time without time zone NOT NULL,
  is_closed           boolean NOT NULL DEFAULT FALSE,
  CHECK (open_time <> close_time)
);

-- Generic salon settings (key/value)
CREATE TABLE salon_settings (
  setting_id          serial PRIMARY KEY,
  setting_key         character varying(50) NOT NULL UNIQUE,
  value               text
);

-- Services offered
CREATE TABLE services (
  service_id          serial PRIMARY KEY,
  name                text NOT NULL,
  description         text,                                -- added: explain what the service includes
  price               numeric(10,2) NOT NULL DEFAULT 0.00,
  duration_minutes    integer NOT NULL DEFAULT 30,
  is_active           boolean NOT NULL DEFAULT TRUE
);

-- Stylists
CREATE TABLE stylists (
  stylist_id          serial PRIMARY KEY,
  name                text NOT NULL,
  experience_years    integer DEFAULT 0,
  specialization      text,                                -- added: stylist specialization
  bio                 text,                                -- added: stylist bio for AI description
  is_active           boolean NOT NULL DEFAULT TRUE
);

-- Mapping table: which stylist can perform which service
CREATE TABLE stylist_services (
  id                  serial PRIMARY KEY,
  stylist_id          integer NOT NULL,
  service_id          integer NOT NULL,
  created_at          timestamp without time zone NOT NULL DEFAULT now(),
  UNIQUE(stylist_id, service_id),
  FOREIGN KEY (stylist_id) REFERENCES stylists(stylist_id) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (service_id)  REFERENCES services(service_id)  ON DELETE CASCADE ON UPDATE CASCADE
);

-- Stylists' availability (per date)
CREATE TABLE stylist_availability (
  availability_id     serial PRIMARY KEY,
  stylist_id          integer NOT NULL,
  date                date NOT NULL,
  start_time          time without time zone NOT NULL,
  end_time            time without time zone NOT NULL,
  CHECK (end_time > start_time),
  created_at          timestamp without time zone NOT NULL DEFAULT now(),
  FOREIGN KEY (stylist_id) REFERENCES stylists(stylist_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Bookings (appointments)
CREATE TABLE bookings (
  booking_id          serial PRIMARY KEY,
  customer_id         integer NOT NULL,
  stylist_id          integer,                             -- nullable: stylist may be unassigned at creation
  service_id          integer,                             -- nullable to allow flexible flows (or historical records)
  booking_date        date NOT NULL,
  start_time          time without time zone NOT NULL,
  end_time            time without time zone NOT NULL,
  status              booking_status NOT NULL DEFAULT 'pending',
  notes               text,                                -- added: booking notes (customer preferences)
  cancellation_reason text,                                -- added: why a booking was cancelled
  created_at          timestamp without time zone NOT NULL DEFAULT now(),
  CHECK (end_time > start_time),
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (stylist_id)  REFERENCES stylists(stylist_id)  ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (service_id)  REFERENCES services(service_id)  ON DELETE SET NULL ON UPDATE CASCADE
);

-- ========== INDEXES & HELPFUL CONSTRAINTS ==========

-- Fast lookups for bookings by stylist & date & time (useful for availability/reservation checks)
CREATE INDEX idx_bookings_stylist_date_time ON bookings (stylist_id, booking_date, start_time);

-- Fast lookup for customer email/phone searches
CREATE INDEX idx_customers_email ON customers (email);
CREATE INDEX idx_customers_phone ON customers (phone_number);

-- Ensure no overlapping availability entries for the same stylist on same date (simple check via exclusion requires btree_gist)
-- Note: This exclusion index is optional and requires the btree_gist extension. Uncomment if you can install the extension.
-- CREATE EXTENSION IF NOT EXISTS btree_gist;
-- CREATE INDEX ux_stylist_availability_no_overlap ON stylist_availability
--   USING gist (stylist_id, daterange(date, date + 1, '[]'), tsrange(start_time::timestamp, end_time::timestamp))
--   WHERE (true);

-- ========== SAMPLE GRANTS (optional) ==========
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_role;

-- ========== NOTES / RECOMMENDATIONS ==========
-- * For voice reminders: use customers.email and customers.phone_number together with bookings.booking_date and start_time.
-- * For stylist introductions in voice: use stylists.name, specialization, and bio.
-- * Service spoken descriptions: use services.description.
-- * For cancellation analytics: use bookings.cancellation_reason and status='cancelled'.
-- * Consider storing timezones if you serve cross-timezone clients (timestamps WITH TIME ZONE or separate tz columns).
