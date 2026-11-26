// Bounded heuristic search for large no-three-in-line sets. The seed is read
// as whitespace-delimited zero-based x y pairs. Each run emits one JSON record.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int gcd(int a, int b) {
    while (b != 0) {
        int remainder = a % b;
        a = b;
        b = remainder;
    }
    return a;
}

struct Line {
    int first;
    int stride;
    int length;
    int weight;
};

struct Grid {
    int order;
    int axis_weight;
    std::vector<Line> lines;
    std::vector<std::vector<int>> incidence;

    Grid(int n, int weight) : order(n), axis_weight(weight), incidence(n * n) {
        // An integer line with at least three lattice points has a primitive
        // step with both coordinates bounded by floor((n-1)/2).
        int span = (n - 1) / 2;
        for (int dx = 0; dx <= span; ++dx) {
            for (int dy = -span; dy <= span; ++dy) {
                if ((dx == 0 && dy <= 0) || gcd(dx, std::abs(dy)) != 1) continue;
                int step = dx * n + dy;
                int line_weight = (dx == 0 || dy == 0) ? weight : 1;
                for (int x = 0; x < n; ++x) {
                    for (int y = 0; y < n; ++y) {
                        if (inside(x - dx, y - dy) || !inside(x + 2 * dx, y + 2 * dy)) continue;
                        int length = 3;
                        while (inside(x + length * dx, y + length * dy)) ++length;
                        int id = static_cast<int>(lines.size());
                        int first = x * n + y;
                        lines.push_back({first, step, length, line_weight});
                        for (int i = 0; i < length; ++i) incidence[first + i * step].push_back(id);
                    }
                }
            }
        }
    }

    bool inside(int x, int y) const {
        return 0 <= x && x < order && 0 <= y && y < order;
    }

    // An independent O(k^3) check uses only the input coordinates and integer
    // determinants. It does not consult the maximal-line enumeration.
    int determinant_energy(const std::vector<int>& points,
                           std::vector<std::array<int, 3>>* triples = nullptr) const {
        std::vector<bool> present(incidence.size());
        int energy = 0;
        for (auto a = points.begin(); a != points.end(); ++a) {
            if (*a < 0 || *a >= static_cast<int>(present.size()) || present[*a]) {
                throw std::logic_error("duplicate or out-of-grid witness point");
            }
            present[*a] = true;
            int ax = *a / order;
            int ay = *a % order;
            for (auto b = a + 1; b != points.end(); ++b) {
                int dx = *b / order - ax;
                int dy = *b % order - ay;
                for (auto c = b + 1; c != points.end(); ++c) {
                    if (dx * (*c % order - ay) == dy * (*c / order - ax)) {
                        energy += (dx == 0 || dy == 0) ? axis_weight : 1;
                        if (triples != nullptr) triples->push_back({{*a, *b, *c}});
                    }
                }
            }
        }
        return energy;
    }
};

class SearchState {
public:
    explicit SearchState(const Grid& board)
        : grid(board), index(board.incidence.size(), -1), penalty(index.size()),
          line_counts(board.lines.size()) {}

    bool has(int point) const { return index[point] >= 0; }
    int size() const { return static_cast<int>(selected.size()); }

    void add(int point) {
        if (has(point)) throw std::logic_error("cannot add a selected point");
        energy += penalty[point];
        for (int id : grid.incidence[point]) {
            int old_count = line_counts[id]++;
            if (old_count > 0) update_other_points(grid.lines[id], point, old_count, 1);
        }
        index[point] = size();
        selected.push_back(point);
    }

    void remove(int point) {
        if (!has(point)) throw std::logic_error("cannot remove a vacant point");
        energy -= penalty[point];
        for (int id : grid.incidence[point]) {
            int new_count = --line_counts[id];
            if (new_count > 0) update_other_points(grid.lines[id], point, new_count, -1);
        }
        int last = selected.back();
        selected[index[point]] = last;
        index[last] = index[point];
        selected.pop_back();
        index[point] = -1;
    }

    void restore(const std::vector<int>& points) {
        while (!selected.empty()) remove(selected.back());
        for (int point : points) add(point);
    }

    const Grid& grid;
    std::vector<int> index;
    std::vector<int> penalty;
    std::vector<int> selected;
    int energy = 0;

private:
    void update_other_points(const Line& line, int pivot, int count, int sign) {
        // For every other point q, toggling the pivot changes the pairs
        // through q by the number of selected points besides q and the pivot.
        for (int i = 0, point = line.first; i < line.length; ++i, point += line.stride) {
            if (point != pivot) penalty[point] += sign * line.weight * (count - has(point));
        }
    }

    std::vector<std::uint8_t> line_counts;
};

using Rng = std::mt19937_64;

int draw(Rng& random, int range) {
    return static_cast<int>(random() % static_cast<std::uint64_t>(range));
}

int choose_addition(const SearchState& state, Rng& random, int noise,
                    const std::vector<std::uint64_t>* tabu = nullptr, std::uint64_t step = 0,
                    int aspiration = -1, const std::vector<bool>* exclude = nullptr) {
    int chosen = -1;
    int best = std::numeric_limits<int>::max();
    int cells = static_cast<int>(state.index.size());
    int point = draw(random, cells);
    for (int checked = 0; checked < cells; ++checked) {
        if (!state.has(point) && (exclude == nullptr || !(*exclude)[point]) && state.penalty[point] < best &&
            (tabu == nullptr || (*tabu)[point] <= step || state.penalty[point] <= aspiration)) {
            int score = state.penalty[point] + (noise == 0 ? 0 : draw(random, noise + 1));
            if (score < best) {
                best = score;
                chosen = point;
                if (best == 0) break;
            }
        }
        if (++point == cells) point = 0;
    }
    return chosen;
}

int choose_removal(const SearchState& state, Rng& random, bool unrestricted) {
    if (unrestricted || state.energy == 0) return state.selected[draw(random, state.size())];
    int picked = -1;
    int count = 0;
    bool prefer_high = draw(random, 3) == 0;
    for (int point : state.selected) {
        if (state.penalty[point] == 0) continue;
        if (prefer_high) {
            if (picked >= 0 && state.penalty[point] < state.penalty[picked]) continue;
            if (picked >= 0 && state.penalty[point] > state.penalty[picked]) count = 0;
        }
        if (draw(random, ++count) == 0) picked = point;
    }
    if (picked == -1) throw std::logic_error("positive energy without an offending point");
    return picked;
}

struct TargetRecord {
    std::vector<int> points;
    int energy = std::numeric_limits<int>::max();
    int deletions = 0;
    std::uint64_t step = 0;
};

struct Archive {
    const Grid& grid;
    const std::vector<int>& seed;
    std::vector<int> valid;
    TargetRecord closest;
    TargetRecord closest_deep;
    int valid_deletions = 0;
    int max_deletions = 0;
    int deepest = 0;
    std::uint64_t deep_trials = 0;
    std::uint64_t accepted_trials = 0;

    Archive(const Grid& board, const std::vector<int>& start, int depth)
        : grid(board), seed(start), valid(start), deepest(depth) {}

    int deletions(const SearchState& state) const {
        return static_cast<int>(std::count_if(seed.begin(), seed.end(),
                                              [&](int point) { return !state.has(point); }));
    }

    void consider(const SearchState& state, bool at_target, std::uint64_t step) {
        int distance = deletions(state);
        max_deletions = std::max(max_deletions, distance);
        if (distance >= deepest) ++deep_trials;
        bool closest_target = at_target && state.energy < closest.energy;
        bool closest_deep_target = at_target && distance >= deepest &&
                                   state.energy < closest_deep.energy;
        bool better_valid = state.energy == 0 &&
            (state.selected.size() > valid.size() ||
                (state.selected.size() == valid.size() && distance > valid_deletions));
        if (closest_target || closest_deep_target || better_valid) {
            if (grid.determinant_energy(state.selected) != state.energy) {
                throw std::logic_error("incremental objective differs from determinant check");
            }
        }
        if (closest_target) closest = {state.selected, state.energy, distance, step};
        if (closest_deep_target) closest_deep = {state.selected, state.energy, distance, step};
        if (better_valid) {
            valid = state.selected;
            valid_deletions = distance;
        }
    }
};

void remove_conflicts(SearchState& state, Rng& random, const std::vector<int>& protected_points) {
    while (state.energy != 0) {
        int chosen = -1;
        int best = 0;
        int ties = 0;
        for (int point : state.selected) {
            int score = state.penalty[point];
            if (score < best || score == 0 ||
                std::find(protected_points.begin(), protected_points.end(), point) != protected_points.end()) {
                continue;
            }
            if (score > best) {
                best = score;
                ties = 0;
            }
            if (draw(random, ++ties) == 0) chosen = point;
        }
        if (chosen == -1) throw std::logic_error("protected points contain a collinear triple");
        state.remove(chosen);
    }
}

void fill_valid(SearchState& state, Rng& random, int target) {
    while (state.size() < target) {
        int next = choose_addition(state, random, 0);
        if (next == -1 || state.penalty[next] != 0) break;
        state.add(next);
    }
}

std::uint64_t tabu_search(SearchState& state, Archive& archive, Rng& random, int target,
                          std::uint64_t budget) {
    // Keep the requested cardinality and temporarily forbid reinserting a point
    // removed by a swap, unless it improves the recorded target score.
    std::vector<std::uint64_t> tabu(state.index.size());
    std::uint64_t step = 0;
    while (step < budget && static_cast<int>(archive.valid.size()) < target) {
        if (step % 3500 == 0) {
            if (step != 0) {
                state.restore(draw(random, 3) == 0 ? archive.seed : archive.closest.points);
                int removals = std::min(state.size(), 6 + draw(random, 26));
                for (int i = 0; i < removals; ++i) state.remove(choose_removal(state, random, true));
                std::fill(tabu.begin(), tabu.end(), 0);
            }
            while (state.size() < target) state.add(choose_addition(state, random, step == 0 ? 0 : 3));
            archive.consider(state, true, step);
            if (state.energy == 0) break;
        }
        int old = choose_removal(state, random, draw(random, 10) == 0);
        state.remove(old);
        tabu[old] = step + 8 + draw(random, 24);
        int noise = draw(random, 6) == 0 ? 1 + draw(random, 6) : 0;
        int aspiration = archive.closest.energy == std::numeric_limits<int>::max() ? -1 :
                         archive.closest.energy - state.energy - 1;
        int next = choose_addition(state, random, noise, &tabu, step, aspiration);
        if (next == -1) next = choose_addition(state, random, 0);
        state.add(next);
        ++step;

        bool project = state.energy < archive.closest.energy || step % 512 == 0;
        archive.consider(state, true, step);
        if (project && state.energy != 0) {
            std::vector<int> points = state.selected;
            remove_conflicts(state, random, {});
            fill_valid(state, random, target);
            archive.consider(state, state.size() == target, step);
            state.restore(points);
        }
    }
    return step;
}

std::uint64_t shake_search(SearchState& state, Archive& archive, Rng& random, int target,
                           std::uint64_t budget) {
    // Start with random deletions and force one or two previously vacant points
    // into the reconstruction before repairing and filling it.
    std::vector<int> current = archive.seed;
    std::uint64_t step = 0;
    while (step < budget && static_cast<int>(archive.valid.size()) < target) {
        if (step % 40 == 0) current = draw(random, 2) == 0 ? archive.seed : archive.valid;
        state.restore(current);
        std::vector<bool> previous(state.index.size());
        for (int point : current) previous[point] = true;
        int removals = std::min(state.size(), 5 + draw(random, step % 12 == 0 ? 44 : 17));
        for (int i = 0; i < removals; ++i) state.remove(choose_removal(state, random, true));
        std::vector<int> novel;
        for (int count = 1 + draw(random, 2); count > 0; --count) {
            int point = choose_addition(state, random, 7, nullptr, 0, -1, &previous);
            if (point == -1) break;
            state.add(point);
            novel.push_back(point);
        }
        remove_conflicts(state, random, novel);
        fill_valid(state, random, target);
        archive.consider(state, state.size() == target, step + 1);
        int loss = static_cast<int>(current.size()) - state.size();
        int distance_from_best = static_cast<int>(archive.valid.size()) - state.size();
        if (loss <= 0 || (distance_from_best <= 4 && loss <= 2 && draw(random, 4) == 0)) {
            current = state.selected;
            ++archive.accepted_trials;
        }
        ++step;
    }
    return step;
}

std::uint64_t pivot_search(SearchState& state, Archive& archive, Rng& random, int target,
                           std::uint64_t budget) {
    // Replace points involved in conflicts with one or two new points, then
    // fill the vacancies. Every accepted state has zero conflicts.
    std::vector<std::uint64_t> tabu(state.index.size());
    std::vector<bool> previous(state.index.size());
    fill_valid(state, random, target);
    archive.consider(state, state.size() == target, 0);
    std::uint64_t step = 0;
    while (step < budget && static_cast<int>(archive.valid.size()) < target) {
        if (step > 0 && step % 1536 == 0) {
            state.restore(draw(random, 4) == 0 ? archive.seed : archive.valid);
            fill_valid(state, random, target);
            archive.consider(state, state.size() == target, step);
            if (state.size() == target) break;
            std::fill(tabu.begin(), tabu.end(), 0);
        }
        std::vector<int> current = state.selected;
        for (int point : current) previous[point] = true;
        std::vector<int> pivots;
        int width = draw(random, 4) == 0 ? 2 : 1;
        for (int i = 0; i < width; ++i) {
            int noise = draw(random, 6) == 0 ? 10 : 2;
            int point = choose_addition(state, random, noise, &tabu, step, -1, &previous);
            if (point == -1) break;
            state.add(point);
            pivots.push_back(point);
            remove_conflicts(state, random, pivots);
            if (state.size() == target) break;
        }
        fill_valid(state, random, target);
        archive.consider(state, state.size() == target, step + 1);
        int loss = static_cast<int>(current.size()) - state.size();
        int distance_from_best = static_cast<int>(archive.valid.size()) - state.size();
        if (loss <= 0 || (distance_from_best <= 3 && loss <= 2 && draw(random, 10) == 0)) {
            for (int point : current) {
                if (!state.has(point)) tabu[point] = step + 3 + draw(random, 14);
            }
            ++archive.accepted_trials;
        } else {
            for (std::size_t i = state.selected.size(); i > 0; --i) {
                int point = state.selected[i - 1];
                if (!previous[point]) state.remove(point);
            }
            for (int point : current) {
                if (!state.has(point)) state.add(point);
            }
        }
        for (int point : current) previous[point] = false;
        ++step;
    }
    return step;
}

void write_point(int order, int point) {
    std::cout << '[' << point / order << ',' << point % order << ']';
}

void write_points(int order, const std::vector<int>& points) {
    std::cout << '[';
    for (std::size_t i = 0; i < points.size(); ++i) {
        if (i != 0) std::cout << ',';
        write_point(order, points[i]);
    }
    std::cout << ']';
}

void write_target(const Grid& grid, TargetRecord& result) {
    if (result.points.empty()) {
        std::cout << "null";
        return;
    }
    std::sort(result.points.begin(), result.points.end());
    std::vector<std::array<int, 3>> triples;
    if (grid.determinant_energy(result.points, &triples) != result.energy) {
        throw std::logic_error("reported target objective differs from determinant check");
    }
    int order = grid.order;
    std::cout << "{\"step\":" << result.step << ",\"collinear_triples\":" << triples.size()
              << ",\"points\":";
    write_points(order, result.points);
    std::cout << ",\"conflicts\":[";
    for (std::size_t i = 0; i < triples.size(); ++i) {
        if (i != 0) std::cout << ',';
        std::cout << '[';
        write_point(order, triples[i][0]);
        std::cout << ',';
        write_point(order, triples[i][1]);
        std::cout << ',';
        write_point(order, triples[i][2]);
        std::cout << ']';
    }
    std::cout << "]}";
}

std::uint64_t positive_integer(const char* argument, std::uint64_t upper) {
    std::string value(argument);
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos) {
        throw std::invalid_argument("expected a positive decimal integer");
    }
    auto result = std::stoull(value);
    if (result == 0 || result > upper) throw std::invalid_argument("integer argument out of range");
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 8) {
            throw std::invalid_argument("usage: local_hunt order target rng_seed budget tabu|shake|pivot axis_weight deep_minimum_deletions < seed.xy");
        }
        int order = static_cast<int>(positive_integer(argv[1], 100));
        int target = static_cast<int>(positive_integer(argv[2], 2 * order));
        std::uint64_t random_seed = positive_integer(argv[3], std::numeric_limits<std::uint64_t>::max());
        std::uint64_t budget = positive_integer(argv[4], std::numeric_limits<std::uint64_t>::max() - 40);
        std::string mode(argv[5]);
        int axis_weight = static_cast<int>(positive_integer(argv[6], 16));
        int depth = static_cast<int>(positive_integer(argv[7], 2 * order));
        if (order < 3 || (mode != "tabu" && mode != "shake" && mode != "pivot")) {
            throw std::invalid_argument("order must be at least 3 and mode must be tabu, shake, or pivot");
        }
        std::vector<int> seed;
        int x, y;
        while (std::cin >> std::ws && std::cin.peek() != std::char_traits<char>::eof()) {
            if (!(std::cin >> x >> y) || x < 0 || x >= order || y < 0 || y >= order) {
                throw std::invalid_argument("expected a valid zero-based x y point");
            }
            seed.push_back(x * order + y);
        }
        if (!std::cin.eof() || seed.empty() || seed.size() >= static_cast<std::size_t>(target)) {
            throw std::invalid_argument("seed must contain fewer points than target");
        }
        auto start = std::chrono::steady_clock::now();
        Grid grid(order, axis_weight);
        if (grid.determinant_energy(seed) != 0) throw std::invalid_argument("seed contains a collinear triple");
        SearchState state(grid);
        state.restore(seed);
        if (state.energy != 0) throw std::logic_error("valid input has nonzero incremental objective");
        Archive archive(grid, seed, depth);
        Rng random(random_seed);
        std::uint64_t steps;
        if (mode == "tabu") steps = tabu_search(state, archive, random, target, budget);
        else if (mode == "shake") steps = shake_search(state, archive, random, target, budget);
        else steps = pivot_search(state, archive, random, target, budget);
        double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::cout << "{\"order\":" << order << ",\"target\":" << target
                  << ",\"rng_seed\":" << random_seed << ",\"method\":\"" << mode
                  << "\",\"axis_weight\":" << axis_weight << ",\"budget\":" << budget
                  << ",\"steps\":" << steps << ",\"seconds\":" << seconds << ",\"seed_size\":" << seed.size()
                  << ",\"best_valid_size\":" << archive.valid.size()
                  << ",\"best_valid_seed_deletions\":" << archive.valid_deletions
                  << ",\"max_seed_deletions\":" << archive.max_deletions
                  << ",\"deep_threshold\":" << depth << ",\"deep_states\":" << archive.deep_trials
                  << ",\"accepted_reconstructions\":" << archive.accepted_trials
                  << ",\"best_target_energy\":";
        if (archive.closest.points.empty()) std::cout << "null";
        else std::cout << archive.closest.energy;
        std::cout << ",\"best_target_seed_deletions\":" << archive.closest.deletions
                  << ",\"best_target_configuration\":";
        write_target(grid, archive.closest);
        std::cout << ",\"best_deep_target_energy\":";
        if (archive.closest_deep.points.empty()) std::cout << "null";
        else std::cout << archive.closest_deep.energy;
        std::cout << ",\"best_deep_target_seed_deletions\":" << archive.closest_deep.deletions
                  << ",\"best_deep_target_configuration\":";
        write_target(grid, archive.closest_deep);
        std::cout << ",\"determinant_verified_witness\":";
        if (grid.determinant_energy(archive.valid) != 0) {
            throw std::logic_error("invalid reported witness");
        }
        std::sort(archive.valid.begin(), archive.valid.end());
        write_points(order, archive.valid);
        std::cout << "}\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
