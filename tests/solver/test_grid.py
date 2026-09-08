from solver import GridDistance, solve_grid_axis_positions


def test_dimension_chain_solves_true_coordinates_in_mm():
    solution = solve_grid_axis_positions(
        [
            GridDistance("A", "B", 6000, "c-ab"),
            GridDistance("B", "C", 4500, "c-bc"),
            GridDistance("C", "D", 3000, "c-cd"),
            GridDistance("A", "D", 13500, "c-ad-total"),
        ],
        origin_axis="A",
    )

    assert solution.solved
    assert solution.positions == {"A": 0.0, "B": 6000.0, "C": 10500.0, "D": 13500.0}


def test_dimension_conflict_is_reported_not_averaged():
    solution = solve_grid_axis_positions(
        [
            GridDistance("A", "B", 6000, "c-ab"),
            GridDistance("B", "C", 4500, "c-bc"),
            GridDistance("A", "C", 10000, "c-ac-wrong-total"),
        ],
        origin_axis="A",
    )

    assert not solution.solved
    assert solution.positions["C"] == 10500.0
    assert any(conflict.constraint_id == "c-ac-wrong-total" for conflict in solution.conflicts)


def test_disconnected_dimension_graph_is_rejected():
    try:
        solve_grid_axis_positions(
            [
                GridDistance("A", "B", 6000, "c-ab"),
                GridDistance("X", "Y", 3000, "c-xy"),
            ],
            origin_axis="A",
        )
    except ValueError as exc:
        assert "disconnected" in str(exc)
    else:
        raise AssertionError("disconnected graph must not silently solve")
