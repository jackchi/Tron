(ns tronweb2.core
  (:require [reagent.core :as reagent]
            [tronweb2.routes :as routes]))

(def app-state (reagent/atom {}))

(defn root []
  [:div.container-fluid
    [:nav.navbar.navbar-expand-lg.navbar-light.bg-light
      [:a.navbar-brand {:href "#/"} "Tron"]

      [:ul.navbar-nav.mr-auto
        [:li.nav-item.active
          [:a.nav-link {:href "#/"} "Jobs" [:span.sr-only "(current)"]]]]
      [:form.form-inline.my-2.my-lg-0
        [:input.form-control.mr-sm-2 {:type "search" :placeholder "Search"}]
        [:button.btn.btn-outline-success.my-2.my-sm-0 {:type "submit"} "Search"]]]
    [:br]
    (let [state @app-state]
      [:div.container
        (for [j (:jobs state)]
          [:div.card.w-25 {:key (j "name")}
            [:div.card-body
              [:h6.card-title (str (j "name"))]
              [:p.card-text
                "qwrf we gert gqe rf wertg ert gq er fw treg w erf qwer f"]]])])])

(defn ^:export init []
  (enable-console-print!)
  (routes/setup app-state)
  (reagent/render [root] (.getElementById js/document "app")))
