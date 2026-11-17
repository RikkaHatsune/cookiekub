--
-- PostgreSQL database dump
--

\restrict ruRc5wWonCpG1Gi3hOMzsgdzmtxikBU3ZzpdSEmZG0Wo9mugl7hhGqJc5t1sTk3

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_audit (
    id bigint NOT NULL,
    actor_user_id bigint,
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE admin_audit; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.admin_audit IS 'Журнал действий админов; details без PII';


--
-- Name: admin_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_audit ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.admin_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: cafes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cafes (
    id bigint NOT NULL,
    slug text NOT NULL,
    name text NOT NULL,
    address text NOT NULL,
    phone text DEFAULT ''::text NOT NULL,
    opens_at time without time zone NOT NULL,
    closes_at time without time zone NOT NULL,
    map_x numeric(5,2) NOT NULL,
    map_y numeric(5,2) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT cafes_map_x_check CHECK (((map_x >= (0)::numeric) AND (map_x <= (100)::numeric))),
    CONSTRAINT cafes_map_y_check CHECK (((map_y >= (0)::numeric) AND (map_y <= (100)::numeric)))
);


--
-- Name: cafes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.cafes ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cafes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_items (
    id bigint NOT NULL,
    order_id bigint NOT NULL,
    product_id bigint,
    product_name text NOT NULL,
    unit_price_cents integer NOT NULL,
    quantity integer NOT NULL,
    line_total_cents integer NOT NULL,
    CONSTRAINT order_items_line_total CHECK ((line_total_cents = (unit_price_cents * quantity))),
    CONSTRAINT order_items_line_total_cents_check CHECK ((line_total_cents > 0)),
    CONSTRAINT order_items_quantity_check CHECK (((quantity >= 1) AND (quantity <= 99))),
    CONSTRAINT order_items_unit_price_cents_check CHECK ((unit_price_cents > 0))
);


--
-- Name: order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.order_items ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.order_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: order_number_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    id bigint NOT NULL,
    order_number text NOT NULL,
    user_id bigint,
    customer_name text NOT NULL,
    customer_email text NOT NULL,
    customer_phone text DEFAULT ''::text NOT NULL,
    customer_comment text DEFAULT ''::text NOT NULL,
    fulfillment text NOT NULL,
    cafe_id bigint,
    delivery_address text,
    status text DEFAULT 'processing'::text NOT NULL,
    subtotal_cents integer NOT NULL,
    discount_cents integer DEFAULT 0 NOT NULL,
    total_cents integer NOT NULL,
    promo_id bigint,
    promo_code text,
    payment_ref text,
    card_last4 text,
    privacy_consent_at timestamp with time zone,
    paid_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT orders_card_last4_check CHECK (((card_last4 IS NULL) OR (card_last4 ~ '^[0-9]{4}$'::text))),
    CONSTRAINT orders_completed_at CHECK (((status <> 'completed'::text) OR (completed_at IS NOT NULL))),
    CONSTRAINT orders_discount_cap CHECK ((discount_cents <= subtotal_cents)),
    CONSTRAINT orders_discount_cents_check CHECK ((discount_cents >= 0)),
    CONSTRAINT orders_fulfillment_check CHECK ((fulfillment = ANY (ARRAY['pickup'::text, 'delivery'::text]))),
    CONSTRAINT orders_fulfillment_fields CHECK ((((fulfillment = 'pickup'::text) AND (cafe_id IS NOT NULL) AND (delivery_address IS NULL)) OR ((fulfillment = 'delivery'::text) AND (delivery_address IS NOT NULL) AND (cafe_id IS NULL)))),
    CONSTRAINT orders_status_check CHECK ((status = ANY (ARRAY['processing'::text, 'completed'::text, 'cancelled'::text]))),
    CONSTRAINT orders_subtotal_cents_check CHECK ((subtotal_cents >= 0)),
    CONSTRAINT orders_total_cents_check CHECK ((total_cents >= 0)),
    CONSTRAINT orders_totals CHECK ((total_cents = (subtotal_cents - discount_cents)))
);


--
-- Name: TABLE orders; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orders IS 'Заказы; user_id NULL = гостевой заказ; card_last4 — максимум платёжных данных';


--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.orders ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    id bigint NOT NULL,
    slug text NOT NULL,
    name text NOT NULL,
    short_description text DEFAULT ''::text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    price_cents integer NOT NULL,
    image_url text DEFAULT ''::text NOT NULL,
    category text DEFAULT 'classic'::text NOT NULL,
    stock_qty integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT products_price_cents_check CHECK ((price_cents > 0)),
    CONSTRAINT products_stock_qty_check CHECK ((stock_qty >= 0))
);


--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.products ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.products_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: promo_redemptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.promo_redemptions (
    id bigint NOT NULL,
    promo_id bigint NOT NULL,
    order_id bigint NOT NULL,
    user_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: promo_redemptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.promo_redemptions ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.promo_redemptions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: promos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.promos (
    id bigint NOT NULL,
    code text NOT NULL,
    discount_type text NOT NULL,
    percent_value integer,
    amount_cents integer,
    min_order_cents integer DEFAULT 0 NOT NULL,
    max_uses integer,
    used_count integer DEFAULT 0 NOT NULL,
    starts_at timestamp with time zone,
    ends_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT promos_amount_cents_check CHECK ((amount_cents > 0)),
    CONSTRAINT promos_discount_type_check CHECK ((discount_type = ANY (ARRAY['percent'::text, 'fixed'::text]))),
    CONSTRAINT promos_max_uses_check CHECK ((max_uses > 0)),
    CONSTRAINT promos_min_order_cents_check CHECK ((min_order_cents >= 0)),
    CONSTRAINT promos_percent_value_check CHECK (((percent_value >= 1) AND (percent_value <= 100))),
    CONSTRAINT promos_period CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at > starts_at))),
    CONSTRAINT promos_type_values CHECK ((((discount_type = 'percent'::text) AND (percent_value IS NOT NULL) AND (amount_cents IS NULL)) OR ((discount_type = 'fixed'::text) AND (amount_cents IS NOT NULL) AND (percent_value IS NULL)))),
    CONSTRAINT promos_used_count_check CHECK ((used_count >= 0)),
    CONSTRAINT promos_used_count_limit CHECK (((max_uses IS NULL) OR (used_count <= max_uses)))
);


--
-- Name: promos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.promos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.promos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version text NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessions (
    id bigint NOT NULL,
    token_hash text NOT NULL,
    user_id bigint NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sessions IS 'Непрозрачные сессии; хранится только sha256 токена';


--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.sessions ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tickets (
    id bigint NOT NULL,
    user_id bigint,
    email text NOT NULL,
    subject text NOT NULL,
    category text DEFAULT 'other'::text NOT NULL,
    message text NOT NULL,
    status text DEFAULT 'open'::text NOT NULL,
    admin_reply text,
    replied_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tickets_category_check CHECK ((category = ANY (ARRAY['bug'::text, 'question'::text, 'other'::text]))),
    CONSTRAINT tickets_status_check CHECK ((status = ANY (ARRAY['open'::text, 'answered'::text, 'closed'::text])))
);


--
-- Name: tickets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tickets ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.tickets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    full_name text DEFAULT ''::text NOT NULL,
    role text DEFAULT 'user'::text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    privacy_consent_at timestamp with time zone,
    anonymized_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_role_check CHECK ((role = ANY (ARRAY['user'::text, 'admin'::text])))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.users IS 'Аккаунты KubanoID; пароль — scrypt-хэш, PII минимизированы';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.users ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: admin_audit admin_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_audit
    ADD CONSTRAINT admin_audit_pkey PRIMARY KEY (id);


--
-- Name: cafes cafes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cafes
    ADD CONSTRAINT cafes_pkey PRIMARY KEY (id);


--
-- Name: cafes cafes_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cafes
    ADD CONSTRAINT cafes_slug_key UNIQUE (slug);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_order_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_order_number_key UNIQUE (order_number);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: products products_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_slug_key UNIQUE (slug);


--
-- Name: promo_redemptions promo_redemptions_order_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.promo_redemptions
    ADD CONSTRAINT promo_redemptions_order_id_key UNIQUE (order_id);


--
-- Name: promo_redemptions promo_redemptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.promo_redemptions
    ADD CONSTRAINT promo_redemptions_pkey PRIMARY KEY (id);


--
-- Name: promos promos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.promos
    ADD CONSTRAINT promos_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: admin_audit_actor_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_audit_actor_idx ON public.admin_audit USING btree (actor_user_id);


--
-- Name: admin_audit_created_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_audit_created_idx ON public.admin_audit USING btree (created_at DESC);


--
-- Name: order_items_order_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX order_items_order_idx ON public.order_items USING btree (order_id);


--
-- Name: orders_created_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_created_idx ON public.orders USING btree (created_at DESC);


--
-- Name: orders_customer_email_lower_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_customer_email_lower_idx ON public.orders USING btree (lower(customer_email));


--
-- Name: orders_status_paid_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_status_paid_idx ON public.orders USING btree (status, paid_at);


--
-- Name: orders_user_created_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orders_user_created_idx ON public.orders USING btree (user_id, created_at DESC);


--
-- Name: products_active_sort_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX products_active_sort_idx ON public.products USING btree (is_active, sort_order, id);


--
-- Name: products_category_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX products_category_idx ON public.products USING btree (category);


--
-- Name: promo_redemptions_promo_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_redemptions_promo_idx ON public.promo_redemptions USING btree (promo_id);


--
-- Name: promo_redemptions_user_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX promo_redemptions_user_idx ON public.promo_redemptions USING btree (user_id);


--
-- Name: promos_code_lower_uidx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX promos_code_lower_uidx ON public.promos USING btree (upper(code));


--
-- Name: sessions_expires_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sessions_expires_idx ON public.sessions USING btree (expires_at);


--
-- Name: sessions_user_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sessions_user_idx ON public.sessions USING btree (user_id);


--
-- Name: tickets_email_lower_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tickets_email_lower_idx ON public.tickets USING btree (lower(email));


--
-- Name: tickets_status_created_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tickets_status_created_idx ON public.tickets USING btree (status, created_at DESC);


--
-- Name: users_email_lower_uidx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_email_lower_uidx ON public.users USING btree (lower(email));


--
-- Name: cafes cafes_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER cafes_set_updated_at BEFORE UPDATE ON public.cafes FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: orders orders_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER orders_set_updated_at BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: products products_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER products_set_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: promos promos_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER promos_set_updated_at BEFORE UPDATE ON public.promos FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: tickets tickets_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tickets_set_updated_at BEFORE UPDATE ON public.tickets FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: users users_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_set_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: admin_audit admin_audit_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_audit
    ADD CONSTRAINT admin_audit_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL;


--
-- Name: orders orders_cafe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_cafe_id_fkey FOREIGN KEY (cafe_id) REFERENCES public.cafes(id) ON DELETE SET NULL;


--
-- Name: orders orders_promo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_promo_id_fkey FOREIGN KEY (promo_id) REFERENCES public.promos(id) ON DELETE SET NULL;


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: promo_redemptions promo_redemptions_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.promo_redemptions
    ADD CONSTRAINT promo_redemptions_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: promo_redemptions promo_redemptions_promo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.promo_redemptions
    ADD CONSTRAINT promo_redemptions_promo_id_fkey FOREIGN KEY (promo_id) REFERENCES public.promos(id) ON DELETE CASCADE;


--
-- Name: promo_redemptions promo_redemptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.promo_redemptions
    ADD CONSTRAINT promo_redemptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tickets tickets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict ruRc5wWonCpG1Gi3hOMzsgdzmtxikBU3ZzpdSEmZG0Wo9mugl7hhGqJc5t1sTk3

