#include "fare_parser.h"
#include "utils/csv.h"
#include "ed/data.h"

#include <boost/foreach.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/spirit/include/qi.hpp>
#include <boost/spirit/include/qi_lit.hpp>
#include <boost/spirit/include/phoenix_core.hpp>
#include <boost/spirit/include/phoenix_operator.hpp>
#include <boost/lexical_cast.hpp>

#include <boost/fusion/include/adapt_struct.hpp>

/// Wrapper pour pouvoir parser une condition en une seule fois avec boost::spirit::qi
namespace fa = navitia::fare;
BOOST_FUSION_ADAPT_STRUCT(
    fa::Condition,
    (std::string, key)
    (fa::Comp_e, comparaison)
    (std::string, value)
)

namespace greg = boost::gregorian;
namespace qi = boost::spirit::qi;
namespace ph = boost::phoenix;

namespace ed { namespace connectors {

void fare_parser::load() {
    load_prices();

    load_transitions();

    load_od();
}

//void fare_parser::parse_files(Data& data){
//    parse_prices(data);
//    parse_trasitions(data);
//    parse_origin_destinations(data);
//}

std::vector<fa::Condition> parse_conditions(const std::string & conditions){
    std::vector<fa::Condition> ret;
    std::vector<std::string> string_vec;
    boost::algorithm::split(string_vec, conditions, boost::algorithm::is_any_of("&"));
    for (const std::string & cond_str : string_vec) {
        ret.push_back(parse_condition(cond_str));
    }
    return ret;
}

fa::State parse_state(const std::string & state_str){
    fa::State state;
    if (state_str == "" || state_str == "*")
        return state;
    for (fa::Condition cond : parse_conditions(state_str)) {
        if(cond.comparaison != fa::Comp_e::EQ) throw invalid_key();
        if(cond.key == "line"){
            if(state.line != "") throw invalid_key();
            state.line = cond.value;
        }
        else if(cond.key == "zone"){
            if(state.zone != "") throw invalid_key();
            state.zone = cond.value;
        }
        else if(cond.key == "mode"){
            if(state.mode != "") throw invalid_key();
            state.mode = cond.value;
        }
        else if(cond.key == "stoparea"){
            if(state.stop_area != "") throw invalid_key();
            state.stop_area = cond.value;
        }
        else if(cond.key == "network"){
            if(state.network != "") throw invalid_key();
            state.network = cond.value;
        }
        else if(cond.key == "ticket"){
            if(state.ticket != "") throw invalid_key();
            state.ticket = cond.value;
        }
        else{
            throw invalid_key();
        }
    }

    return state;
}

fa::Condition parse_condition(const std::string & condition_str) {
    std::string str = boost::algorithm::to_lower_copy(condition_str);
    boost::algorithm::replace_all(str, " ", "");
    fa::Condition cond;

    if(str.empty())
        return cond;

    // Match du texte : du alphanumérique et quelques chars spéciaux
    qi::rule<std::string::iterator, std::string()> txt = +(qi::alnum|qi::char_("_:-"));

    // Tous les opérateurs que l'on veut matcher et leur valeur associée
    qi::rule<std::string::iterator, fa::Comp_e()> operator_r = qi::string("<=")[qi::_val = fa::Comp_e::LTE]
                                                         | qi::string(">=")[qi::_val = fa::Comp_e::GTE]
                                                         | qi::string("!=")[qi::_val = fa::Comp_e::NEQ]
                                                         | qi::string("<") [qi::_val = fa::Comp_e::LT]
                                                         | qi::string(">") [qi::_val = fa::Comp_e::GT]
                                                         | qi::string("=")[qi::_val = fa::Comp_e::EQ];

    // Une condition est de la forme "txt op txt"
    qi::rule<std::string::iterator, fa::Condition()> condition_r = txt >> operator_r >> txt ;

    std::string::iterator begin = str.begin();
    std::string::iterator end = str.end();

    // Si on n'arrive pas à tout parser
    if(!qi::phrase_parse(begin, end, condition_r, boost::spirit::ascii::space, cond) || begin != end) {
        std::cout << "impossible de parser la condition " << condition_str << std::endl;
        throw invalid_condition();
    }
    return cond;
}


void fare_parser::load_transitions() {
    CsvReader reader(state_transition_filename);
    std::vector<std::string> row;
    reader.next(); //en-tête

    for (row = reader.next(); !reader.eof(); row = reader.next()) {
        bool symetric = false;

        if (row.size() != 6) {
            LOG4CPLUS_ERROR(logger, "Wrongly formated line " << row.size() << " columns, we skip the line");
            continue;
        }

        fa::State start = parse_state(row.at(0));
        fa::State end = parse_state(row.at(1));

        fa::Transition transition;
        transition.start_conditions = parse_conditions(row.at(2));
        transition.end_conditions = parse_conditions(row.at(3));
        std::vector<std::string> global_conditions;
        std::string str_condition = boost::algorithm::trim_copy(row.at(4));
        boost::algorithm::split(global_conditions, str_condition, boost::algorithm::is_any_of("&"));

        for (std::string cond : global_conditions) {
           if (cond == "symetric") {
               symetric = true;
           } else {
               transition.global_condition = cond;
           }
        }
        transition.ticket_key = boost::algorithm::trim_copy(row[5]);

        //coherence check
        if (data.fare_map.find(transition.ticket_key) == data.fare_map.end()) {
            LOG4CPLUS_WARN(logger, "impossible to find ticket " << transition.ticket_key << ", transition skipped");
//            continue;
        }

        data.transitions.push_back(std::make_tuple(start, end, transition));

        if (symetric) {
            fa::Transition sym_transition = transition;
            sym_transition.start_conditions = transition.end_conditions;
            sym_transition.end_conditions = transition.start_conditions;
            data.transitions.push_back(std::make_tuple(start, end, sym_transition));
        }
    }
}

void fare_parser::load_prices() {
    CsvReader reader(prices_filename);
    for (std::vector<std::string> row = reader.next() ; ! reader.eof() ; row = reader.next()) {
        // La structure du csv est : clef;date_debut;date_fin;prix;libellé
        greg::date start(greg::from_undelimited_string(row.at(1)));
        greg::date end(greg::from_undelimited_string(row.at(2)));
        data.fare_map[row.at(0)].add(start, end,
                             fa::Ticket(row.at(0), row.at(4), boost::lexical_cast<int>(row.at(3)), row.at(4)) );
    }
}

fa::OD_key::od_type to_od(const std::string& key) {
    std::string lower_key = boost::algorithm::to_lower_copy(key);
    if (lower_key == "mode")
        return fa::OD_key::Mode;
    if (lower_key == "zone")
        return fa::OD_key::Zone;
    if (lower_key == "stop" || lower_key == "stoparea")
        return fa::OD_key::StopArea;
    throw navitia::exception("Unable to parse " + key + " as Od_Key");
}

void fare_parser::load_od() {
    CsvReader reader(od_filename);
    std::vector<std::string> row;
    reader.next(); //en-tête

    // file format is :
    // Origin ID, Origin name, Origin mode, Destination ID, Destination name, Destination mode, ticket_id, ticket id, .... (with any number of ticket)

    int count = 0;
    for (row=reader.next(); !reader.eof(); row = reader.next()) {

        if (row.size() < 7) {
            LOG4CPLUS_WARN(logger, "wrongly formated OD line : " << boost::algorithm::join(row, ", "));
            continue;
        }
        std::string start_saec = boost::algorithm::trim_copy(row[0]);
        std::string dest_saec = boost::algorithm::trim_copy(row[3]);
        //col 1 and 3 are the human readable name of the start/end, and are not used

        std::string start_mode = boost::algorithm::trim_copy(row[2]);
        std::string dest_mode = boost::algorithm::trim_copy(row[5]);

        std::vector<std::string> price_keys;
        for (int i = 6; i < row.size(); ++i) {
            std::string price_key = boost::algorithm::trim_copy(row[i]);

            if (price_key.empty())
                continue;

            //coherence check
            if (data.fare_map.find(price_key) == data.fare_map.end()) {
                LOG4CPLUS_WARN(logger, "impossible to find ticket " << price_key << ", od ticket skipped");
//                continue; //do we have to skip the entire OD ?
            }

            price_keys.push_back(price_key);
        }

        fa::OD_key start(to_od(start_mode), start_saec), dest(to_od(dest_mode), dest_saec);
        data.od_tickets[start][dest] = price_keys;

        count++;
    }
    LOG4CPLUS_INFO(logger, "Nombre de tarifs OD Île-de-France : " << count);
}

}
}
