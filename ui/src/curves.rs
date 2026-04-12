pub fn ease_in_out_cubic(t: f32) -> f32 {
    let t = t % 1.0;
    if t < 0.5 {
        4.0 * t * t * t
    } else {
        1.0 - (-2.0 * t + 2.0).powi(3) / 2.0
    }
}
